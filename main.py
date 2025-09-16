"""Entry point for running the Meeting Recorder Gradio app."""

from meeting_recorder import create_app


def main() -> None:
    """Launch the Gradio interface."""

    app = create_app()
    app.launch()


if __name__ == "__main__":
    main()
