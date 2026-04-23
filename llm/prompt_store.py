from os import listdir
from os.path import isdir

PROMPTS_DIR = "prompts"


class PromptStore:
    __builtin_prompts__ = ["system", "summary"]
    system: str
    summary: str
    _others: dict[str, str]

    def __init__(self) -> None:
        self.system = ""
        self.summary = ""
        self._others = {}

        if not isdir(PROMPTS_DIR):
            return

        for prompt_file in filter(
            lambda f: f.endswith(".md"),
            listdir(PROMPTS_DIR)
        ):
            with open(f"{PROMPTS_DIR}/{prompt_file}", "r", encoding="utf-8") as f:
                content = f.read()

            prompt_name = prompt_file[:-3]
            if prompt_name == "system":
                self.system = content
            elif prompt_name == "summary":
                self.summary = content
            else:
                self._others[prompt_name] = content

    def __getattr__(self, name: str) -> str:
        if name in self.__builtin_prompts__:
            return super().__getattribute__(name)
        if name in self._others:
            return self._others[name]
        return ""

    def __getitem__(self, name: str) -> str:
        return self.__getattr__(name)

    def get_all_prompts(self) -> dict[str, str]:
        return {
            **self._others,
            **{
                name: getattr(self, name)
                for name in self.__builtin_prompts__
            },
        }
