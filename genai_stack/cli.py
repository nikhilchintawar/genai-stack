"""Console script for genai_stack."""
import json
import logging
import logging.handlers
import sys

import click

from genai_stack import __version__
from genai_stack.core import ConfigLoader
from genai_stack.constants import (
    CUSTOM_MODEL_KEY_NAME,
    MODEL_CONFIG_KEY,
    RETRIEVER_CONFIG_KEY,
    VECTORDB_CONFIG_KEY,
)
from genai_stack.constants.install import AVAILABLE_COMPONENTS, Components
from genai_stack.constants.model import AVAILABLE_MODEL_MAPS
from genai_stack.etl.run import run_etl_loader
from genai_stack.exception import GenAIStackException
from genai_stack.install.installer import Installer
from genai_stack.model.run import (
    get_model_class,
    get_retriever_class,
    get_vectordb_class,
    list_supported_models,
    run_custom_model,
)
from genai_stack.utils.model import create_default_model_json_file
from genai_stack.utils.run import execute_command_in_directory

BANNER = """
 ██████╗ ███████╗███╗   ██╗ █████╗ ██╗    ███████╗████████╗ █████╗  ██████╗██╗  ██╗
██╔════╝ ██╔════╝████╗  ██║██╔══██╗██║    ██╔════╝╚══██╔══╝██╔══██╗██╔════╝██║ ██╔╝
██║  ███╗█████╗  ██╔██╗ ██║███████║██║    ███████╗   ██║   ███████║██║     █████╔╝
██║   ██║██╔══╝  ██║╚██╗██║██╔══██║██║    ╚════██║   ██║   ██╔══██║██║     ██╔═██╗
╚██████╔╝███████╗██║ ╚████║██║  ██║██║    ███████║   ██║   ██║  ██║╚██████╗██║  ██╗
 ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝    ╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
"""

logger = logging.getLogger(__name__)


class LLMStackCommand(click.Group):
    def get_help(self, ctx: click.Context) -> str:
        return f"{BANNER}{super().get_help(ctx)}"


@click.group(cls=LLMStackCommand)
def main():
    click.echo(BANNER)


@main.command()
def version():
    """Version of the installed GenAI Stack package

    `genai-stack version`
    """
    click.echo(f"Version - {__version__}")


@main.command()
def list_models():
    """Lists available prebuilt models

    `genai-stack list-models`
    """
    click.echo("Available List of models\n")
    for indx, model in enumerate(list_supported_models()):
        click.echo(f"{indx+1}. {model}")


@main.command()
@click.option("--config_file", help="Config file", type=str)
def start(config_file):
    """Start a HTTP server for a model

    `genai-stack start --model gpt3.5`
    """
    if not config_file:
        logger.warning("No Config file provided, creating a default one.")
        config_file = create_default_model_json_file()
    config_loader = ConfigLoader(config=config_file)

    try:
        vectordb_client = get_vectordb_class(
            config_loader.get_config_section_name(
                VECTORDB_CONFIG_KEY,
            )
        )(config=config_file)
    except ValueError as e:
        logger.warning(f" Failed to Initialize VectorDB - {e}")
        vectordb_client = None

    try:
        retriever = get_retriever_class(
            config_loader.get_config_section_name(
                RETRIEVER_CONFIG_KEY,
            )
        )(config=config_file, vectordb=vectordb_client)
    except ValueError as e:
        logger.warning(f" Failed to Initialize Retriever - {e}")
        retriever = None

    model: str = config_loader.get_config_section_name(MODEL_CONFIG_KEY)
    model = model.strip()
    if model == CUSTOM_MODEL_KEY_NAME:
        return run_custom_model(
            config_loader=config_loader,
            retriver=retriever,
            config_file=config_file,
        )
    if model not in AVAILABLE_MODEL_MAPS.keys():
        raise GenAIStackException(
            "Unkown Prebuilt Model Provided. Checkout how to run a custom model with GenAI Stack."  # noqa: E501
        )
    model_class = get_model_class(model)(config=config_file, retriever=retriever)
    model_class.run_http_server()


@main.command()
@click.option("--config_file", help="Config file", type=str)
def etl(config_file):
    """Running an ETL process"""
    config_loader = ConfigLoader(config=config_file)

    try:
        vectordb = get_vectordb_class(
            config_loader.get_config_section_name(
                VECTORDB_CONFIG_KEY,
            )
        )(config=config_file)
    except ValueError as e:
        logger.warning(f" Failed to Initialize VectorDB - {e}")
        default_config = {
            "name": "chromadb",
            "class_name": "genai_stack",
            "fields": {
                "persistent_path": "<YOUR DIR PATH TO PERSIST EMBEDDING DATA>"
            },  # A temp directory to persist the vector embeddings
        }

        logger.info(f"Set up a default vectordb with these configs: {default_config}")
        raise e

    run_etl_loader(config_file=config_file, vectordb=vectordb)


@main.command()
@click.option(
    "-destination",
    help="Download and Install Airbyte",
    type=str,
    required=True,
)
def dli_airbyte(destination):
    """Download and install airbyte"""
    click.echo("Downloading and installing Airbyte")
    execute_command_in_directory(
        target_directory=destination,
        commands=[
            "git clone https://github.com/airbytehq/airbyte.git",
            "cd airbyte",
            "./run-ab-platform.sh",
        ],
    )


@main.command()
@click.option("--component", required=False, help="Specify the component.")
@click.option("--subcomponent", required=False, help="Specify the subcomponent")
@click.option("--list-components", is_flag=True, help="List all the components and subcomponents available")
@click.option("--quickstart", is_flag=True, help="Use quickstart mode.")
@click.option("--config-file", help="Config file for installing your component", type=str)
def install(component, subcomponent, list_components, quickstart, config_file):
    if list_components:
        click.echo("Available components for installation")
        comp_string = "Components: \n"
        for idx, component in enumerate(Components):
            comp_string += f"\t {idx + 1}. {component.value} \n"
            comp_string += "\t\t Subcomponents: \n"
            for subcomponent in AVAILABLE_COMPONENTS[component]:
                comp_string += f"\t\t\t * {subcomponent} \n"

        click.echo(comp_string.format(components=comp_string))

    if component and subcomponent:
        if quickstart:
            Installer(component, subcomponent, quickstart=True).install()

        elif config_file:
            # JSON file is provided, load and parse the JSON data
            with open(config_file, "r") as file:
                options = json.load(file)
                Installer(component, subcomponent, options=options).install()


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
