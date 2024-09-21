
import PIL.Image as Image
import io
from tools.graph import GraphTool
from langchain_core.runnables.graph import MermaidDrawMethod

## Generate our LangGraph Diagram using Mermaid and saving the image using PIL.
app = GraphTool()
graph = app.get_graph_app()
raw_diagram = graph.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.API)
image = Image.open(io.BytesIO(raw_diagram))
image.save("images/eve_diagram.png")