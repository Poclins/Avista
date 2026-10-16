"""NetworkStack — red mínima para la arquitectura serverless de jAImes.

Módulo H (Infraestructura como Código, AWS CDK en Python). Provisiona *lo
justo* para que la Lambda de cómputo alcance Aurora Serverless v2 y los
servicios AWS gestionados, sin sobre-dimensionar (base razonable de MVP, no
endurecimiento avanzado). Ver ``docs/cloud/cdk.md`` (tabla de stacks) como
fuente de verdad de la composición.

Decisiones de diseño:

- **VPC mínima** con dos AZ (requisito de Aurora) y subredes privadas con
  salida controlada. Se evita el coste de NAT Gateways usando **endpoints de
  VPC** para los servicios que la Lambda necesita: así la función corre
  *in-VPC* (para hablar con Aurora por red privada) y sigue alcanzando S3,
  Secrets Manager y Bedrock sin exponer tráfico a Internet.
- **Gateway endpoint** para S3 (sin coste por hora).
- **Interface endpoints** para Secrets Manager (credenciales de BD),
  Bedrock runtime (LLM + embeddings) y CloudWatch Logs (observabilidad).
  Transcribe/Textract/Rekognition se invocan vía los endpoints públicos de la
  API gestionada; para el MVP no se añaden sus interface endpoints (se pueden
  sumar en endurecimiento posterior).

La VPC se exporta como atributo para que `DataStack` (Aurora) y `ComputeStack`
(Lambda) la referencien por cruce de stacks desde ``app.py``.
"""

from __future__ import annotations

from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from constructs import Construct


class NetworkStack(Stack):
    """VPC mínima + endpoints de VPC para la pila serverless de jAImes."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC mínima: 2 AZ (Aurora exige al menos dos) y subredes privadas
        # aisladas (PRIVATE_ISOLATED) para no pagar NAT Gateways. La
        # conectividad hacia AWS se resuelve con endpoints de VPC más abajo.
        self.vpc = ec2.Vpc(
            self,
            "JaimesVpc",
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="jaimes-publica",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="jaimes-privada",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        # --- Gateway endpoint: S3 (medios cifrados). Sin coste por hora. ---
        self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )

        # --- Interface endpoints: servicios que la Lambda invoca in-VPC. ---
        # Secrets Manager: credenciales de BD (Requirement 11.6).
        self.vpc.add_interface_endpoint(
            "SecretsManagerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
        )
        # Bedrock runtime: LLM (Claude) + embeddings (Titan).
        self.vpc.add_interface_endpoint(
            "BedrockRuntimeEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.BEDROCK_RUNTIME,
        )
        # CloudWatch Logs: registro de errores/trazas de la Lambda.
        self.vpc.add_interface_endpoint(
            "CloudWatchLogsEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
        )
