import time
import pickle
import openai
import faiss
import numpy as np
from config import openai_api_key
from openai.error import (
  ServiceUnavailableError,
  APIError,
  APIConnectionError,
)

openai.api_key = openai_api_key  # Use from the config instead of hardcoding

EMBD_MODEL = "text-embedding-ada-002"
EMBD_DIM = 1536  # get with embeds_np.shape[1]


DATABASE_FILENAME = "memories/dummy.pkl"

initial_dummy_data = [
  "User Name: Rodrigo Werneck Franco",
  "User Birth Date: 02/26/1991",
  "The user is a professional software engineer",
  "User Favorite Programming Language: Python",
  "User Favorite Programming Framework for web development: NodeJS",
]

class VectorstoreDatabase:
  def __init__(self, initial_data=None, save_file=DATABASE_FILENAME):
    self.EMBD_MODEL = "text-embedding-ada-002"
    self.retry_wait_time = 10
    self.data = []
    self.index = None
    self.save_file = save_file
  
    # Load data from file if it exists, else load initial data and stores it, thus creating the file.
    if self._load_from_file():
      print("Loaded data from file.")
    else:
      self._create_index()
      if initial_data:
        self.add(initial_data)
      else:
        self._save_to_file()
  
  def _get_embeddings(self, data):
    while True:
      try:
        res = openai.Embedding.create(
          input=data, 
          model=self.EMBD_MODEL
        )
      except (
        ServiceUnavailableError,
        APIConnectionError,
      ):
        print(f"retrying in {self.retry_wait_time} seconds...")
        time.sleep(self.retry_wait_time)
      except APIError as err:
        error_code = err and err.json_body and isinstance(err.json_body, dict) and err.json_body.get("error")
        error_code = error_code and error_code.get("code")
        if error_code == "content_filter":
          raise
        print(f"retrying in {self.retry_wait_time} seconds...")
        time.sleep(self.retry_wait_time)
      else:
        break
    embeds = [record['embedding'] for record in res['data']]
    return embeds
  
  def _load_from_file(self):
    try:
      with open(self.save_file, "rb") as f:
        self.data, self.index = pickle.load(f)
        return True
    except FileNotFoundError:
      print("No save file found, starting with empty database.")
      return False

  def _create_index(self):
    embeds = self._get_embeddings(["This is just a dummy string placeholder"])
    embeds_np = np.array(embeds).astype('float32')
    self.index = faiss.IndexFlatIP(embeds_np.shape[1])

  def _add_to_index(self, new_data):
    if not isinstance(new_data, list):
      new_data = [new_data]
    embeds = self._get_embeddings(new_data)
    embeds_np = np.array(embeds).astype('float32')
    self.index.add(embeds_np)

  def _remove_from_index(self, data):
    xq = self._get_embeddings([data])[0]
    xq_np = np.array([xq]).astype('float32')
    _, I = self.index.search(xq_np, 1)
    self.index.remove_ids(I[0])

  # TODO: fix this function and put it back to work:
  # The following commented function is wrong because it removes the old data from a place and insert the new one into another
  # to fix it, we must add_with_ids and store each id in its corresponding data entry
  # def _edit_from_index(self, old_data, new_data):
  #   self._remove_from_index(old_data) 
  #   self._add_to_index([new_data])

  def _rebuilt_index(self):
    self._create_index()
    self._add_to_index(self.data)
  
  def _save_to_file(self):
    with open(self.save_file, "wb") as f:
      pickle.dump((self.data, self.index), f, protocol=pickle.HIGHEST_PROTOCOL)

  def add(self, entries):
    if not isinstance(entries, list):
      entries = [entries]
    self.data.extend(entries)
    self._add_to_index(entries) # Only update index for the new entries
    self._save_to_file()
    return True
  
  def search(self, query, n_results=3):
    xq = self._get_embeddings([query])[0]
    xq_np = np.array([xq]).astype('float32')
    D, I = self.index.search(xq_np, n_results)
    res = []
    for i in I[0]:
        entry = self.data[i]
        if entry not in res:
          res.append(entry)
    
    print(f"Vectorstore database Query: {query} results: ------------------------")
    print(res)
    print("--------------------------------------------------------------")

    if len(res) == 0:
      return False
    return res

  def replace(self, old_entry, new_entry):
    if old_entry in self.data:
      index = self.data.index(old_entry)
      self.data[index] = new_entry
      self._rebuilt_index()
      self._save_to_file()
      print(f"Vectorstore database modified entry: {old_entry} to {new_entry}")
      return True
    else:
      return False
  
  def remove(self, entry):
    if entry in self.data:
      self.data.remove(entry)
      self._rebuilt_index()
      self._save_to_file()
      return True
    else:
      return False

if __name__ == "__main__":
  # Usage:
  
  db = VectorstoreDatabase(initial_dummy_data)

  # db.search("What is my favorite programming language?", 2)

  print(db.data)
  db.search("What is the User Name?", 2)
  # db.replace("User Name: Rodrigo Werneck Franco", "User Name: Rodrigo Franco")
  db.replace("User Name: Rodrigo Franco", "User Name: Rodrigo Werneck Franco")
  db.search("What is the User Name?", 2)

  db.add("The Beatles is the user's favorite band.")
  db.search("What band the user likes?", 2)
  # db.replace("User Birth Date: 02/26/1991", "User Birth Date: 02/02/2000")
  # db.search("User Name", 2)