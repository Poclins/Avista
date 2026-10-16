"""DataStack — capa de datos de jAImes: Aurora Serverless v2, S3 y secretos.

Módulo H (AWS CDK en Python). Provisiona la **capa 3** (acceso a datos) de la
arquitectura serverless, siguiendo ``docs/cloud/cdk.md``:

- **Aurora Serverless v2 (PostgreSQL + ``pgvector``):** un solo motor cubre la
  base relacional (personas/entidades) y la vectorial (embeddings para RAG)
  (Requirement 4.6). ``pgvector`` es una *extensión* de Postgres que se crea en
  tiempo de *seed* (``CREATE EXTENSION vector``); aquí solo se garantiza una
  versión de motor que la soporta. Autoescalado v2 (escala a poco en reposo).
- **Credenciales en AWS Secrets Manager** (Requirement 11.6): el cluster genera
  y rota su secreto de credenciales; nunca viajan en código ni en variables de
  entorno en texto plano.
- **Bucket S3 cifrado** para los medios (Requirement 11.4): cifrado en reposo
  (SSE gestionado por S3), bloqueo total de acceso público y política que
  **fuerza SSL** (``enforce_ssl``). Las URLs prefirmadas (vigencia ≤300 s) las
  emite la aplicación en tiempo de ejecución, no la infraestructura.

El cluster vive en la VPC de `NetworkStack` (subredes privadas aisladas). La
VPC, el cluster, el secreto y el bucket se exponen como atributos para que
`ComputeStack` los referencie por cruce de stacks desde ``app.py``.

> MVP, no endurecimiento avanzado: capacidades mínimas de Aurora, retención y
> claves gestionadas por AWS. ``removal_policy=DESTROY`` facilita limpiar el
> entorno de hackathon (en producción sería ``RETAIN``). Verificable del todo
> solo en *deploy* real (tarea 11.3), no en ``cdk synth``.
"""

from __future__ import annotations

from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_rds as rds
from aws_cdk import aws_s3 as s3
from constructs import Construct


class DataStack(Stack):
    """Aurora Serverless v2 (pgvector) + bucket S3 cifrado + Secrets Manager."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc: ec2.IVpc,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = vpc

        # ------------------------------------------------------------------
        # Grupos de seguridad (definidos aquí para evitar referencias cíclicas
        # entre stacks): un SG para el cluster y un SG dedicado "cliente" que
        # `ComputeStack` adjuntará a la Lambda. La regla de ingreso al puerto de
        # Aurora se autoriza **dentro de este stack** (DataStack), de modo que
        # ComputeStack solo dependa de DataStack y no al revés.
        # ------------------------------------------------------------------
        self.db_security_group = ec2.SecurityGroup(
            self,
            "AuroraSecurityGroup",
            vpc=vpc,
            description="jAImes Aurora Serverless v2 (acceso solo desde la Lambda)",
            allow_all_outbound=True,
        )

        # SG que llevará la Lambda; se expone para ComputeStack.
        self.lambda_security_group = ec2.SecurityGroup(
            self,
            "LambdaClienteSecurityGroup",
            vpc=vpc,
            description="jAImes Lambda (cliente de Aurora)",
            allow_all_outbound=True,
        )

        # Ingreso al puerto por defecto de Postgres (5432) solo desde la Lambda.
        self.db_security_group.add_ingress_rule(
            peer=self.lambda_security_group,
            connection=ec2.Port.tcp(5432),
            description="Acceso de la Lambda de jAImes a Aurora",
        )

        # ------------------------------------------------------------------
        # Aurora Serverless v2 (PostgreSQL + pgvector).
        # El motor PostgreSQL 15.x soporta la extensión pgvector (creada en el
        # seed con `CREATE EXTENSION vector`). Credenciales autogeneradas y
        # guardadas en Secrets Manager (Requirement 11.6).
        # ------------------------------------------------------------------
        self.db_credentials = rds.Credentials.from_generated_secret(
            username="jaimes_admin",
            secret_name="jaimes/aurora/credenciales",
        )

        self.database = rds.DatabaseCluster(
            self,
            "JaimesAurora",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                # .of() fija una versión disponible en la cuenta/región sin depender
                # del enum de aws-cdk-lib (que puede estar desfasado). 15.10
                # es no-limitless y soporta pgvector.
                version=rds.AuroraPostgresEngineVersion.of("15.10", "15"),
            ),
            credentials=self.db_credentials,
            # Serverless v2: autoescalado entre capacidades mínimas (escala a
            # poco en reposo, Requirement 17.1 / 18.3).
            serverless_v2_min_capacity=0.5,
            serverless_v2_max_capacity=4,
            writer=rds.ClusterInstance.serverless_v2("writer"),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            ),
            security_groups=[self.db_security_group],
            default_database_name="jaimes",
            storage_encrypted=True,
            # Entorno de hackathon: destruir al limpiar. En producción: RETAIN.
            removal_policy=RemovalPolicy.DESTROY,
        )

        # El secreto de credenciales que la Lambda leerá en runtime (puede ser
        # None si se pasara un secreto externo; con credenciales generadas
        # siempre existe).
        self.db_secret = self.database.secret

        # ------------------------------------------------------------------
        # Bucket S3 de medios cifrados (Requirement 11.4).
        # Cifrado en reposo (SSE-S3), sin acceso público, SSL forzado. Las URLs
        # prefirmadas (≤300 s) las genera la app, no la infraestructura.
        # ------------------------------------------------------------------
        self.media_bucket = s3.Bucket(
            self,
            "JaimesMediaBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    # Limpia subidas multiparte incompletas (higiene de costes).
                    abort_incomplete_multipart_upload_after=Duration.days(7),
                ),
            ],
        )
