import os
import sys
import requests

from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
from langchain_community.llms import Ollama
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.text_splitter import RecursiveCharacterTextSplitter


class SuppressStdout:
	def __enter__(self):
		self._original_stdout = sys.stdout
		self._original_stderr = sys.stderr
		sys.stdout = open(os.devnull, "w")
		sys.stderr = open(os.devnull, "w")

	def __exit__(self, exc_type, exc_val, exc_tb):
		sys.stdout.close()
		sys.stdout = self._original_stdout
		sys.stderr = self._original_stderr


class RagWebpage:
	vectorstore = None
	retriever = None
	qa_chain = None

	def __init__(self) -> None:
		self.template = """Use the following pieces of context to answer the question at the end. 
		If you don't know the answer, just say that you don't know, don't try to make up an answer. 
		Use three sentences maximum and keep the answer as concise as possible. 
		Context: {context}
		Question: {question}
		Helpful Answer:"""
		self.prompt = PromptTemplate(
			input_variables=["context", "question"],
			template=self.template,
		)
		self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=0)

	def ingest(self, model:str, web_url_list: list[str]):
		data = []
		for web_url in web_url_list:
			resp = requests.get(url=web_url)
			if resp.status_code >= 300:
				raise Exception("Invalid URL")
			else:
				# load the webpage 
				loader = WebBaseLoader(web_path=web_url)
				docs = loader.load()
				data.extend(docs)

		self.llm = Ollama(model=model, callback_manager=CallbackManager([StreamingStdOutCallbackHandler()]))

		#Split the webpage content into chunks
		all_splits = self.text_splitter.split_documents(data)
		with SuppressStdout():
			vectorstore = Chroma.from_documents(documents=all_splits, embedding=GPT4AllEmbeddings())

		self.retriever=vectorstore.as_retriever(
			search_type="similarity_score_threshold",
			search_kwargs={
				"k": 3,
				"score_threshold": 0.5,
			}
		)

		# Chain
		self.qa_chain = (
			{"context": self.retriever, "question": RunnablePassthrough()}
			| self.prompt
			| self.llm
			| StrOutputParser()
		)

	def ask(self, query: str) -> str:
		if not self.qa_chain:
			return "Please, add a webpage url first."
		return self.qa_chain.invoke(query)

	def clear(self):
		self.vectorstore = None
		self.retriever = None
		self.qa_chain = None

