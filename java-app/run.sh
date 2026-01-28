param(
  [string]$DatabaseUrl = "postgresql://shop:shop@<LINUX_HOST_IP>:5432/shop",
  [string]$BadQueryMode = "like",
  [int]$Port = 8081
)

# Windows Java runtime (OSS):
# - Eclipse Temurin (preferred): https://adoptium.net/
# - Microsoft Build of OpenJDK
# - Amazon Corretto
#
# Build:
#   mvn -q -DskipTests package
#
# Run (UNINSTRUMENTED):
#   $env:DATABASE_URL = $DatabaseUrl
#   $env:BAD_QUERY_MODE = $BadQueryMode
#   $env:PORT = "$Port"
#   java -cp "target\shop-java-1.0.0.jar;target\deps\*" com.example.shop.App
#
# Run (CANDIDATE: instrument with OpenTelemetry Java agent):
#   1) Download java agent:
#      https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases
#   2) Example:
#      $env:OTEL_SERVICE_NAME = "shop-java"
#      $env:OTEL_EXPORTER_OTLP_ENDPOINT = "http://<LINUX_HOST_IP>:4318"
#      $env:OTEL_EXPORTER_OTLP_PROTOCOL = "http/protobuf"
#      $env:OTEL_TRACES_EXPORTER = "otlp"
#      $env:OTEL_METRICS_EXPORTER = "otlp"
#      java -javaagent:C:\path\opentelemetry-javaagent.jar -cp "target\shop-java-1.0.0.jar;target\deps\*" com.example.shop.App

$env:DATABASE_URL = $DatabaseUrl
$env:BAD_QUERY_MODE = $BadQueryMode
$env:PORT = "$Port"

Write-Host "Running shop-java (uninstrumented) on port $Port"
java -cp "target\shop-java-1.0.0.jar;target\deps\*" com.example.shop.App
