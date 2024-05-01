import subprocess
import streamlit as st
from streamlit_chat import message
from streamlit_tags import st_tags
from rag_webpage import RagWebpage


st.set_page_config(page_title="RagWebpage")


def display_messages():
	st.subheader("Chat")
	for i, (msg, is_user) in enumerate(st.session_state["messages"]):
		message(msg, is_user=is_user, key=str(i))
	st.session_state["thinking_spinner"] = st.empty()


def process_input():
	if st.session_state["user_input"] and len(st.session_state["user_input"].strip()) > 0:
		user_text = st.session_state["user_input"].strip()
		with st.session_state["thinking_spinner"], st.spinner(f"Thinking"):
			agent_text = st.session_state["assistant"].ask(user_text)

		st.session_state["messages"].append((user_text, True))
		st.session_state["messages"].append((agent_text, False))


def read_webpage(model:str, url_list:str):
	st.session_state["assistant"].clear()
	st.session_state["messages"] = []
	st.session_state["user_input"] = ""

	with st.session_state["ingestion_spinner"], st.spinner(f'Ingesting {url_list}'):
		st.session_state["assistant"].ingest(model, url_list)


def page():
	if len(st.session_state) == 0:
		st.session_state["messages"] = []
		st.session_state["assistant"] = RagWebpage()

	st.header("ChatWebPage")

	st.subheader("Input")
	cmd =  "ollama list | awk '{print $1}'"
	ps = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
	output = ps.communicate()[0]
	model_list = (output.decode('utf-8').strip().split('\n')[1:])

	with st.form("user_input_form"):
		model_name = st.selectbox(label="Select You Model", options=model_list, index=None)
		web_urls = st_tags(label="Enter the Web Page URL(s)", text="Hint: Press enter to add multiple URL")
		submit = st.form_submit_button('Submit')
	
	if submit:
		# Validate inputs
		if not model_name or len(web_urls) == 0:
			st.error('Please insert valid inputs', icon="🚨")
		read_webpage(model=model_name, url_list=web_urls)
	
	st.session_state["ingestion_spinner"] = st.empty()

	display_messages()
	st.text_input("Message", key="user_input", on_change=process_input)


if __name__ == "__main__":
	page()

