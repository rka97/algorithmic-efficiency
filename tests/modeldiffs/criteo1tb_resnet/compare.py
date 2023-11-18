import os

# Disable GPU access for both jax and pytorch.
os.environ['CUDA_VISIBLE_DEVICES'] = ''

import jax
import numpy as np
import torch

from algorithmic_efficiency import spec
from algorithmic_efficiency.workloads.criteo1tb.criteo1tb_jax.workload import \
    Criteo1TbDlrmSmallResNetWorkload as JaxWorkload
from algorithmic_efficiency.workloads.criteo1tb.criteo1tb_pytorch.workload import \
    Criteo1TbDlrmSmallResNetWorkload as PytWorkload
from tests.modeldiffs.diff import out_diff


def key_transform(k):
  print('key transform: ')
  new_key = []
  s_count = 0
  resnet_count = 0
  print(k)
  for i in k:
    print(f'in transform {i}')
    if 'Sequential' in i:
      s_count = int(i.split('_')[1])
      continue
    if 'Embedding' in i:
      return ('embedding_table',)
    if 'ResNetBlock' in i:
      i = i.replace('ResNetBlock', 'Dense')
      name, count = i.split('_')
      resnet_count = resnet_count + 1 
      continue
    if 'Linear' in i:
      i = i.replace('Linear', 'Dense')
      name, count = i.split('_')
      i = name + '_' + str(s_count * 3 + int(resnet_count))
    elif 'weight' in i:
      i = i.replace('weight', 'kernel')
    print(f'out transform {i}')
    new_key.append(i)
  print(f'new key {new_key}')
  return tuple(new_key)


def sd_transform(sd):
  out = {}
  chunks = []
  for k in sd:
    if 'embedding_chunk' in ''.join(k):
      chunks.append(sd[k].cpu())
    else:
      out[k] = sd[k]
  out[('embedding_table',)] = torch.cat(chunks, dim=0)
  return out


if __name__ == '__main__':
  # pylint: disable=locally-disabled, not-callable

  jax_workload = JaxWorkload()
  pytorch_workload = PytWorkload()

  pyt_batch = {
      'inputs': torch.ones((2, 13 + 26)),
      'targets': torch.randint(low=0, high=1, size=(2,)),
      'weights': torch.ones(2),
  }
  jax_batch = {k: np.array(v) for k, v in pyt_batch.items()}

  # Test outputs for identical weights and inputs.
  pytorch_model_kwargs = dict(
      augmented_and_preprocessed_input_batch=pyt_batch,
      model_state=None,
      mode=spec.ForwardPassMode.EVAL,
      rng=None,
      update_batch_norm=False)

  jax_model_kwargs = dict(
      augmented_and_preprocessed_input_batch=jax_batch,
      mode=spec.ForwardPassMode.EVAL,
      rng=jax.random.PRNGKey(0),
      update_batch_norm=False)

  out_diff(
      jax_workload=jax_workload,
      pytorch_workload=pytorch_workload,
      jax_model_kwargs=jax_model_kwargs,
      pytorch_model_kwargs=pytorch_model_kwargs,
      key_transform=key_transform,
      sd_transform=sd_transform,
      out_transform=None)
