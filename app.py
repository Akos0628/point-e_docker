import sys
from PIL import Image
import torch
import matplotlib.pyplot as plt
from tqdm.auto import tqdm

from point_e.diffusion.configs import DIFFUSION_CONFIGS, diffusion_from_config
from point_e.diffusion.sampler import PointCloudSampler
from point_e.models.download import load_checkpoint
from point_e.models.configs import MODEL_CONFIGS, model_from_config
from point_e.util.pc_to_mesh import marching_cubes_mesh
from point_e.util.plotting import plot_point_cloud
from point_e.util.point_cloud import PointCloud

from flask import Flask, request, jsonify, send_file
import warnings

app = Flask(__name__)

@app.route('/', methods=['POST'])
def generate_object():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # Set a prompt to condition on.
    request_data = request.get_json()
    prompt = request_data['prompt']

    # Produce a sample from the model.
    samples = None
    for x in tqdm(sampler.sample_batch_progressive(batch_size=1, model_kwargs=dict(texts=[prompt]))):
        samples = x

    pc = sampler.output_to_point_clouds(samples)[0]

    # Produce a mesh (with vertex colors)
    mesh = marching_cubes_mesh(
        pc=pc,
        model=model,
        batch_size=4096,
        grid_size=128, # increase to 128 for resolution used in evals
        progress=True,
    )

    # Write the mesh to a PLY file to import into some other program.
    with open('mesh.ply', 'wb') as plz:
        mesh.write_ply(plz)

    #with open('cloud.ply', 'wb') as plz:
    #    pc.write_ply(plz)

    return send_file('mesh.ply')

@app.route('/test', methods=['GET'])
def load_last():
    return send_file('mesh.ply')


device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
if not torch.cuda.is_available():
    warnings.warn('no GPU is available')


print()
print('creating base model...')
base_name = 'base40M-textvec'
base_model = model_from_config(MODEL_CONFIGS[base_name], device)
base_model.eval()
base_diffusion = diffusion_from_config(DIFFUSION_CONFIGS[base_name])

print('creating upsample model...')

print('creating upsample model...')
upsampler_model = model_from_config(MODEL_CONFIGS['upsample'], device)
upsampler_model.eval()
upsampler_diffusion = diffusion_from_config(DIFFUSION_CONFIGS['upsample'])

print('downloading base checkpoint...')
base_model.load_state_dict(load_checkpoint(base_name, device))

print('downloading upsampler checkpoint...')
upsampler_model.load_state_dict(load_checkpoint('upsample', device))

sampler = PointCloudSampler(
    device=device,
    models=[base_model, upsampler_model],
    diffusions=[base_diffusion, upsampler_diffusion],
    num_points=[1024, 4096 - 1024],
    aux_channels=['R', 'G', 'B'],
    guidance_scale=[3.0, 0.0],
    model_kwargs_key_filter=('texts', ''), # Do not condition the upsampler at all
)

print('creating SDF model...')
name = 'sdf'
model = model_from_config(MODEL_CONFIGS[name], device)
model.eval()

print('loading SDF model...')
model.load_state_dict(load_checkpoint(name, device))

if __name__ == '__main__':
    app.run(host='0.0.0.0')