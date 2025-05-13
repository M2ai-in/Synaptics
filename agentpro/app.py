import gradio as gr
from run_agent_once import run_agent_once
def gradio_interface(user_input):
    output = run_agent_once(user_input)
    return output
demo = gr.Interface(fn=gradio_interface, inputs=gr.Textbox(lines=3, placeholder="Input here.."), outputs="text", title="Agent-Pro : M2ai", description="A Gradio demo for our optimized agent pipeline forked from traversaal.ai")
if __name__ == "__main__":
    demo.launch()
