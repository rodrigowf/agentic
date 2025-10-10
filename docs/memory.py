import re
import json
import pickle
import autogen
from autogen.agentchat.agent import Agent
from autogen import AssistantAgent, UserProxyAgent, ConversableAgent
from typing import Callable, Dict, List, Optional, Union, Tuple, Any

from summarizer import Summarizer
from vectorstore import VectorstoreDatabase
from memories.dummy_data import dummy_data, dummy_data_descriptions

DATABASE_PATH = "memories"
LOCAL_DATA_FILE = f"{DATABASE_PATH}/short_therm_memory.txt"
DATABASE_INDEX_FILE = f"{DATABASE_PATH}/index.pkl"

config_list = autogen.config_list_from_models(model_list=["gpt-4", "gpt-4-32k", "gpt-4-32k-0314", "gpt-4-32k-v0314", "gpt-4-0613"], exclude="aoai")


llm_config_fn = {
    "functions": [
        {
            "name": "overwrite_short_therm_memory",
            "description": "Overwrites the SHORT TERM MEMORY content with new information. You should provide the full new content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "full_new_content": {
                        "type": "string",
                        "description": "The full new content to replace the current SHORT TERM MEMORY content.",
                    },
                },
                "required": ["full_new_content"],
            },
        },
        {
            "name": "add_to_memory",
            "description": "Adds information to a specified MEMORY BANK. You should provide the MEMORY BANK name and the information to be stored.",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_name": {
                        "type": "string",
                        "description": "the name of the MEMORY BANK to add information to.",
                    },
                    "information": {
                        "type": "string",
                        "description": "The textual information to be stored in the specified MEMORY BANK.",
                    }
                },
                "required": ["memory_name", "information"],
            },
        },
        {
            "name": "search_memory",
            "description": "Searches a specified MEMORY BANK for a given string. You should provide the MEMORY BANK name and the search string. The results are ordered by similarity with your search_query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_name": {
                        "type": "string",
                        "description": "the name of the MEMORY BANK to search.",
                    },
                    "search_query": {
                        "type": "string",
                        "description": "The text used for similarity search in the specified MEMORY BANK. This must be as descriptive and descriptive as possible. This property is required and cannot be empty.",
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "How many similar results to return. Minimum 2, maximum 10.",
                        "default": 3,
                    },
                },
                "required": ["memory_name", "search_string"],
            },
        },
        {
            "name": "replace_data",
            "description": "Replaces information in a specified MEMORY BANK. You should provide the MEMORY BANK name, the old information to be replaced and the new information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_name": {
                        "type": "string",
                        "description": "the name of the MEMORY BANK to modify information in.",
                    },
                    "old_information": {
                        "type": "string",
                        "description": "The old information to be replaced.",
                    },
                    "new_information": {
                        "type": "string",
                        "description": "The new information to replace the old information.",
                    },
                },
                "required": ["memory_name", "old_information", "new_information"],
            },
        },
        {
            "name": "remove_data",
            "description": "Deletes information from a specified MEMORY BANK. You should provide the MEMORY BANK name and the information to be deleted.",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_name": {
                        "type": "string",
                        "description": "the name of the MEMORY BANK to delete information from.",
                    },
                    "information": {
                        "type": "string",
                        "description": "The information to be deleted from the specified MEMORY BANK.",
                    },
                },
                "required": ["memory_name", "information"],
            },
        },
        {
            "name": "create_memory_bank",
            "description": "Creates a new MEMORY BANK. You should provide the MEMORY BANK name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_name": {
                        "type": "string",
                        "description": "the name of the new MEMORY BANK to be created.",
                    },
                    "description": {
                        "type": "string",
                        "description": "a short description of the new MEMORY BANK including the size of its entries.",
                    }
                    # "initial_data": {
                    #     "type": "array",
                    #     "description": "an array of strings to be used as initial data for the new MEMORY BANK.",
                    #     "items": {
                    #         "type": "string",
                    #     },
                    # }    
                },
                "required": ["memory_name"],
            },
        },
        # {
        #     "name": "delete_memory_bank",
        #     "description": "Deletes a specified MEMORY BANK. You should provide the MEMORY BANK name.",
        #     "parameters": {
        #         "type": "object",
        #         "properties": {
        #             "memory_name": {
        #                 "type": "string",
        #                 "description": "the name of the MEMORY BANK to be deleted.",
        #             },
        #         },
        #         "required": ["memory_name"],
        #     },
        # },
        # {
        #     "name": "digest",
        #     "description": "Digests full content from external source into memory. You should provide the source url or path, the name of the new MEMORY BANK and the content type",
        #     "parameters": {
        #         "type": "object",
        #         "properties": {
        #             "source": {
        #                 "type": "string",
        #                 "description": "the url or path of the content to be digested",
        #             },
        #             "bank_name": {
        #                 "type": "string",
        #                 "description": "the name of the new MEMORY BANK to be created",
        #             },
        #             "summarize": {
        #                 "type": "boolean",
        #                 "description": "Indicates if a summary of the entire content should be included in the memory and returned to you",
        #                 "default": False,
        #             },
        #         },
        #         "required": ["source", "bank_name"],
        #     }
        # }
    ],
    "config_list": config_list,
    "request_timeout": 120,
}


class MemoryAssistant:
    def _get_system_message(self):
        return f"""
You are the Memory Agent, a component of a powerful AI system that uses LLM powered multi-agents conversations to accomplish goals for the user.
As a Memory Agent, your role is to smartly manage two memory mechanisms: SHORT TERM MEMORY and the MEMORY BANKS. Do this to answer to the Assistant Admin what they asked for. 

```SHORT TERM MEMORY
{self.st_memory}
```
You can modify or add to the SHORT TERM MEMORY by calling "overwrite_short_therm_memory" function with the full rewritten content. 
The updated version will be sent back to you in your next iteration. Keep it within 4k tokens to fit the context window limit. Excess information should be stored in the respective MEMORY BANKs.

```MEMORY BANKS
{self.memory_descriptions}
```

The MEMORY BANKS use vectorstores and are searchable by text similarity. Manage them efficiently using the provided functions. 
Always search the appropriate memory banks for any input. Request multiple results based on the memory entry size to balance between relevance and space efficiency.
Search before adding something to avoid duplicates and to keep consistency by modifying data when needed. 
Create new memory banks for anything that doesn't fit the existing ones.

You can also digest full content from external sources into new memory banks. Use the "digest" function for this.

You should only use the provided functions and avoid performing any other actions. 
After processing the user's query, formulate a coherent response that aligns with the user's input and the information you've gathered. And finish it with the word 'TERMINATE'.
"""

    def __init__(self):
        self.llm_config = llm_config_fn

        self.st_memory = self._get_st_memory()
        self.memory_banks = {}
        self.memory_descriptions = {}

        self.proxy_system_message="Only use the functions you have been provided with. Do not perform other actions than executing the functions. Except when the task is complete. Then, respond with TERMINATE."
        self.assistant_system_message = self._get_system_message()

        self.memory_assistant = AssistantAgent(
            name="memory_assistant",
            llm_config=self.llm_config,
            system_message=self.assistant_system_message,
        )
        self.memory_proxy = UserProxyAgent(
            name="memory_proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
            system_message=self.proxy_system_message,
            function_map={
                "overwrite_short_therm_memory": self._overwrite_short_therm_memory,
                "add_to_memory": self._add_to_memory,
                "search_memory": self._search_memory,
                "replace_data": self._replace_data,
                "remove_data": self._remove_data,
                "create_memory_bank": self._create_memory_bank,
                # "delete_memory": self._delete_memory,                
            },
            is_termination_msg=self._is_termination_msg,
        )

        self._load_memory_banks()

    def _is_termination_msg(self, content):
        have_content = content.get("content", None) is not None
        if have_content and "TERMINATE" in content["content"]:
            return True
        return False

    def _get_st_memory(self):
        st_memory = ""
        # Load st_memory from .txt file with the same name
        with open(LOCAL_DATA_FILE, "r") as f:
            st_memory = f.read()
        return st_memory
    
    def _update_index_file(self):
        with open(DATABASE_INDEX_FILE, 'wb') as f:
            memory_dict = {key: self.memory_descriptions[key] for key in self.memory_banks.keys()}
            pickle.dump(memory_dict, f, protocol=pickle.HIGHEST_PROTOCOL)
    
    def _load_memory_banks(self):
        print("Loading MEMORY BANKs...")
        try:
            with open(DATABASE_INDEX_FILE, 'rb') as f:
                print("Loading from index file.")
                memory_dict = pickle.load(f)
                for memory_name, description in memory_dict.items():
                    self._create_memory_bank(memory_name, description)
                    self.memory_descriptions[memory_name] = description
        except FileNotFoundError:
            print("Index not found. Creating MEMORY BANKs from dummy data.")
            for memory_name in dummy_data:
                description = dummy_data_descriptions[memory_name]
                self._create_memory_bank(memory_name, description, dummy_data[memory_name])
                self.memory_descriptions[memory_name] = description
            self._update_index_file()

        print("MEMORY BANK ----------------------")
        print(self.memory_banks)
        print(self.memory_descriptions)
        print("-----------------------------------")
        return self.memory_banks
    
    def _refresh_system_message(self):
        self.assistant_system_message = self._get_system_message()
        self.memory_assistant._oai_system_message = [{"content": self.assistant_system_message, "role": "system"}]
    

    # agent functions: -----------------------------------------

    def _overwrite_short_therm_memory(self, full_new_content):
        self.st_memory = full_new_content
        self._refresh_system_message()
        with open(LOCAL_DATA_FILE, "w") as f:
            f.write(self.st_memory)
        return "Local data updated."

    def _add_to_memory(self, memory_name, information):
        self.memory_banks[memory_name].add(information)
        return "Added entry to the MEMORY BANK."

    def _search_memory(self, memory_name, search_query, n_results=3):
        results = self.memory_banks[memory_name].search(search_query, n_results=n_results)
        if results:
            results = "\n".join(results)
        else:
            results = "No results found."
        return results
    
    def _replace_data(self, memory_name, old_information, new_information):
        res = self.memory_banks[memory_name].replace(old_information, new_information)
        if res:
            return f"Entry modified: {old_information} -> {new_information}"
        else:
            return "Entry not found in the memory."

    def _remove_data(self, memory_name, information):
        res = self.memory_banks[memory_name].remove(information)
        if res:
            return f"Entry removed: {information}"
        else:
            return "Entry not found in the MEMORY BANK."

    def _create_memory_bank(self, memory_name, description, initial_data=None):
        # print(f"Creating memory: {memory_name}")
        self.memory_banks[memory_name] = VectorstoreDatabase(
            initial_data=initial_data, 
            save_file=f"{DATABASE_PATH}/{memory_name}.pkl"
        )
        self.memory_descriptions[memory_name] = description
        self._update_index_file()
        self._refresh_system_message()
        return f"MEMORY BANK {memory_name} created."
    
    def _delete_memory(self, memory_name):
        del self.memory_banks[memory_name]
        del self.memory_descriptions[memory_name]
        self._update_index_file()
        self._refresh_system_message()
        return f"MEMORY BANK {memory_name} deleted."
    
    # ----------------------------------------------------------

    def digest(self, source, bank_name, summarize=False):
        """Digests full content from external source into memory"""
        url_pattern = re.compile('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        if url_pattern.match(source):
            source_type = "url"
        else:
            source_type = "file"
        summarizer = Summarizer(source, content_type=source_type, goal=False)
        if summarize:
            summary = summarizer._summarize()
        else:
            summarizer._load_chunks()
            summary = None
        
        chunks = summarizer.chunks

        self._create_memory_bank(
            bank_name, 
            f"Content extracted from: {source}", 
            f"Summary of content extracted from: {source} \n{summary}" if summarize else None
        )
        self._add_to_memory(bank_name, chunks)
        
        res = f"The content from {source} was digested into {bank_name} memory bank" 
        if summarize:
            res += f"alongside its SPR summary. \nSummary: \n{summary}"
        return res 
    
    def append_oai_message(self, message: Union[Dict, str], role, sender):
        self.memory_proxy._append_oai_message(message, role, sender)
        self.memory_assistant._append_oai_message(message, role, sender)

    def append_messages(self, messages, sender):
        for message in messages:
            self.append_oai_message(message, "user", sender)

    def chat(self, messages):
        message = ""
        if isinstance(messages, str):
            message = messages
        else:
            message = messages[-1]["content"]
            self.append_messages(messages[:-1], self.memory_proxy)

        self.memory_proxy.initiate_chat(
            self.memory_assistant,
            message=message,
            clear_history=False
        )
        last_msg = self.memory_assistant.last_message()
        last_msg_content = last_msg["content"].replace("TERMINATE", "")
        print(" FINAL OUTPUT: ====================================================================")
        print(last_msg_content)
        print("===================================================================================")
        return last_msg_content

class MemoryAgent(ConversableAgent):
    def __init__(
        self,
        name: str = "memory_agent",
        role: str = "stores and retrieves information from memory banks"
    ):
        super().__init__(
            name,
            llm_config=llm_config_fn,
        )

        self.memory_assistant = MemoryAssistant()
        self.role = role
        
        # Register a custom reply function.
        self.register_reply(Agent, MemoryAgent._generate_memory_assistant_reply, 1)

    def digest(self, source, bank_name, content_type="raw", return_summary=False):
        self.memory_assistant.digest(source, bank_name, content_type, return_summary)

    def _generate_memory_assistant_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,  # Persistent state.
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """
        Generates a reply to the last user message, after querying the web for relevant information.
        """
        if messages is None:
            # Merge all lists in the dict into a single one.
            messages = [message for sublist in self._oai_messages.values() for message in sublist]

        response_text = self.memory_assistant.chat(messages)

        return True, response_text

if __name__ == "__main__":
    assistant = MemoryAssistant()

    # assistant.chat("User input: Where do i work?")
    # assistant.chat("User input: What is the month i was born?")

    assistant.chat("User input: What kind of music do i like?")
    # assistant.chat("User input: What instruments do i play?")
    # assistant.chat("User input: Remember that the instrument i play the best is the acoustic guitar.")
    # assistant.chat("User input: What is my best instrument?")

    assistant.chat("User input: What technologies are you made from?")
    assistant.chat("User input: What is AutoGen?")

    # assistant.chat("User input: I have to go to the dentist on friday. Please remember it as a task on a new tasks memory bank.")
    # assistant.chat("User input: My dentist appointment changed from friday to saturday. Don't forget.") 
    # assistant.chat("User input: What tasks do i have for friday?")
    # assistant.chat("User input: What is my next task?")

    # assistant.chat("User input: I married and changed my name to Rodrigo Werneck Franco Sueiro. Please remeber it")
    # assistant.chat("User input: What is my name?")
