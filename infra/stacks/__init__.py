"""Paquete de stacks CDK de jAImes (Módulo H).

Cada stack tiene una responsabilidad acotada (SRP) y se compone por cruce de
referencias desde ``app.py`` (ver ``docs/cloud/cdk.md``):

- :class:`~stacks.network_stack.NetworkStack` — VPC mínima + endpoints de VPC.
- :class:`~stacks.data_stack.DataStack` — Aurora Serverless v2 (pgvector),
  bucket S3 cifrado y credenciales en Secrets Manager.
- :class:`~stacks.compute_stack.ComputeStack` — Lambda (FastAPI+Mangum) tras un
  HTTP API de API Gateway, con ``USE_MOCKS=false`` y acceso mínimo a datos.
- :class:`~stacks.ai_iam_stack.AiIamStack` — IAM de mínimos privilegios para
  Bedrock, Transcribe, Textract y Rekognition sobre el rol de la Lambda.

El stack de andamiaje (``placeholder_stack``) de la tarea 11.1 queda retirado
del cableado de ``app.py``; el módulo se conserva solo como referencia.
"""

from stacks.ai_iam_stack import AiIamStack
from stacks.compute_stack import ComputeStack
from stacks.data_stack import DataStack
from stacks.network_stack import NetworkStack

__all__ = [
    "NetworkStack",
    "DataStack",
    "ComputeStack",
    "AiIamStack",
]
