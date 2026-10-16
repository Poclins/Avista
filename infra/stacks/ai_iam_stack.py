"""AiIamStack — permisos IAM de **mínimos privilegios** para los servicios de IA.

Módulo H (AWS CDK en Python). Concede al **rol de ejecución de la Lambda** de
`ComputeStack` únicamente las acciones de IA que la aplicación invoca realmente
(Requirement 11.6, privilegios mínimos), siguiendo ``docs/cloud/cdk.md``:

- **Amazon Bedrock:** solo ``InvokeModel`` (y su variante *stream*), acotado a
  los ARN de los modelos que usa jAImes — Claude (LLM) y Titan (embeddings)—,
  no a ``*`` de modelos. (Ver ``backend/app/providers/llm`` y ``.../embeddings``.)
- **Amazon Transcribe:** solo las acciones del ciclo de un *transcription job*
  (iniciar, consultar). Transcribe no admite ARN de recurso por acción en su
  API de jobs, por lo que el *recurso* es ``*`` pero el conjunto de **acciones**
  queda estrictamente acotado.
- **Amazon Textract:** solo OCR síncrono de documentos (``DetectDocumentText``,
  ``AnalyzeDocument``).
- **Amazon Rekognition:** solo las acciones de análisis de video que usa el
  procesamiento de medios (iniciar/obtener detección de etiquetas).

Se evita todo comodín de acción (``bedrock:*``, ``transcribe:*``…). Donde el
servicio no soporta permisos a nivel de recurso para la operación, el *recurso*
es ``*`` pero las acciones se mantienen mínimas (práctica aceptada de IAM).

Este stack **no crea recursos nuevos**: recibe el ``IRole`` de la Lambda (su rol
de ejecución) desde ``app.py`` y le adjunta las políticas. Así los permisos de
IA quedan en un stack dedicado y auditable, separado del cómputo.
"""

from __future__ import annotations

from aws_cdk import Stack
from aws_cdk import aws_iam as iam
from constructs import Construct

# Modelos Bedrock que jAImes invoca (deben coincidir con la config del backend
# y con las env vars de ComputeStack). Se acota el permiso a estos foundation
# models mediante ARN construidos con la región/cuenta del stack.
_BEDROCK_MODEL_IDS = (
    "anthropic.claude-3-haiku-20240307-v1:0",  # LLM (bitácora/recomendación)
    "amazon.titan-embed-text-v2:0",            # embeddings (RAG)
)


class AiIamStack(Stack):
    """Políticas IAM de mínimos privilegios para Bedrock/Transcribe/Textract/Rekognition."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        lambda_role: iam.IRole,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.lambda_role = lambda_role

        # --- Bedrock: solo InvokeModel, acotado a los ARN de los modelos. ---
        bedrock_model_arns = [
            f"arn:aws:bedrock:{self.region}::foundation-model/{model_id}"
            for model_id in _BEDROCK_MODEL_IDS
        ]
        lambda_role.add_to_principal_policy(
            iam.PolicyStatement(
                sid="BedrockInvokeModelosJaimes",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=bedrock_model_arns,
            )
        )

        # --- Transcribe: ciclo de vida de un transcription job (acciones mínimas). ---
        # La API de jobs de Transcribe no admite ARN por recurso, por lo que el
        # recurso es "*" pero las acciones quedan estrictamente acotadas.
        lambda_role.add_to_principal_policy(
            iam.PolicyStatement(
                sid="TranscribeJobsJaimes",
                effect=iam.Effect.ALLOW,
                actions=[
                    "transcribe:StartTranscriptionJob",
                    "transcribe:GetTranscriptionJob",
                ],
                resources=["*"],
            )
        )

        # --- Textract: OCR síncrono de notas manuscritas (foto). ---
        lambda_role.add_to_principal_policy(
            iam.PolicyStatement(
                sid="TextractOcrJaimes",
                effect=iam.Effect.ALLOW,
                actions=[
                    "textract:DetectDocumentText",
                    "textract:AnalyzeDocument",
                ],
                resources=["*"],
            )
        )

        # --- Rekognition: detección de etiquetas en video (metadatos de escena). ---
        lambda_role.add_to_principal_policy(
            iam.PolicyStatement(
                sid="RekognitionVideoJaimes",
                effect=iam.Effect.ALLOW,
                actions=[
                    "rekognition:StartLabelDetection",
                    "rekognition:GetLabelDetection",
                ],
                resources=["*"],
            )
        )
