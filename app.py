import logging

import pathway as pw
from dotenv import load_dotenv
from pathway.xpacks.llm.question_answering import SummaryQuestionAnswerer
from pathway.xpacks.llm.servers import QASummaryRestServer
from pydantic import BaseModel, ConfigDict, InstanceOf
import os
import tempfile
import yaml

# To use advanced features with Pathway Scale, get your free license key from
# https://pathway.com/features and paste it below.
# To use Pathway Community, comment out the line below.
#pw.set_license_key("demo-license-key-with-telemetry")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

load_dotenv()


class App(BaseModel):
    question_answerer: InstanceOf[SummaryQuestionAnswerer]
    host: str = "0.0.0.0"
    port: int = 8080

    with_cache: bool = True
    terminate_on_error: bool = False

    def run(self) -> None:
        server = QASummaryRestServer(self.host, self.port, self.question_answerer)
        server.run(
            with_cache=self.with_cache,
            terminate_on_error=self.terminate_on_error,
            cache_backend=pw.persistence.Backend.filesystem("Cache"),
        )

    model_config = ConfigDict(extra="forbid")

def load_app_config():
    with open("app.yaml", "r") as f:
        app_config = yaml.safe_load(f)

    # Get the secret from environment variable (set in Cloud Run deployment)
    gdrive_credentials_secret = os.environ.get("default-service")

    if gdrive_credentials_secret:
        # Create a temporary file to store the credentials
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp_file:
            tmp_file.write(gdrive_credentials_secret)
            temp_credentials_file_path = tmp_file.name

        # Update app_config to use the temporary file path
        for pipeline_config in app_config['pipelines'].values():
            for step in pipeline_config['steps'].values():
                if 'uses' in step and step['uses'] == '!pw.io.gdrive.read':
                    step['options']['service_user_credentials_file'] = temp_credentials_file_path
                    break # Assuming only one gdrive.read step per pipeline, adjust if needed
    else:
        print("Warning: default-service environment variable not set. "
              "Using potentially insecure file path from app.yaml if configured.")

    # Get the secret for Gemini API Key from environment variable
    gemini_api_secret = os.environ.get("gemini-api-paid")

    if gemini_api_secret:
        # Update API Key for $llm settings
        if "$llm" in app_config and "api_key" in app_config["$llm"]:
            app_config["$llm"]["api_key"] = gemini_api_secret
        else:
            print("Warning: $llm or api_key not found in app.yaml to update Gemini API key.")

        # Update API Key for $embedder settings
        if "$embedder" in app_config and "api_key" in app_config["$embedder"]:
            app_config["$embedder"]["api_key"] = gemini_api_secret
        else:
            print("Warning: $embedder or api_key not found in app.yaml to update Gemini API key.")
    else:
        print("Warning: gemini-api-paid environment variable not set. "
              "Using potentially insecure API key from app.yaml if configured.")
    
    return app_config

if __name__ == "__main__":
    app_config = load_app_config() # Load and modify app_config with 
    app = App(**app_config) # Instantiate App with the *modified* app_config
    app.run() # Run the REST server
