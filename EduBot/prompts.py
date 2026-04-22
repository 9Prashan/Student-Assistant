# prompts.py
# All PromptTemplate usage has been replaced with plain Python functions so
# there is no dependency on langchain (which is tightly coupled to the OpenAI
# ecosystem and requires its own API-key configuration).
 
# ------------------------------------------------------------------ #
# System prompts                                                       #
# ------------------------------------------------------------------ #
 
bot_sys_prompt = """
You are an AI for personalized and adaptive learning.
"""
 
translator_sys_prompt = """
You are Translator for Science & Mathematics Content.
"""
 
format_content_sys_prompt = """You are a multilingual AI parser. Write the content in formatted.
- use placeholder for image etc.
- Be careful while parsing Latex
Note: Content is in [] and string() is line splitter!
"""
 
# ------------------------------------------------------------------ #
# User-turn prompt builders (replace langchain PromptTemplate)         #
# Each is a plain callable: prompt(key=value, ...) -> str             #
# ------------------------------------------------------------------ #
 
_bot_init_template = """
Problem: {problem}
Solution: {solution}
 
====================
Visualize a team of three specialists collaboratively guiding students to decipher and resolve the provided problem. 
 
- Solution Checker: Assesses the student's responses, focusing keenly on expressions, calculations, and equations.
- Progress Tracker: Monitors the student's progress and outlines the upcoming achievements.
- Mentor: Above all, the Mentor acts as a facilitator rather than a direct problem solver. They review feedback from the Solution Checker and Progress Tracker, and then provide hints and guidance to students, allowing them to learn through doing. The Mentor encourages the student to write equations and solve the problem, awaiting their response before providing further guidance.
 
The interaction flow begins with a motivational boost, followed by pertinent questions to guide the student. The Mentor elaborates on challenging concepts by giving hints rather than direct solutions. The process concludes with a final message once the problem is solved.
 
- Mentor is primary point of contact for student.
 
The team's responses must follow this format:
```
[
SOLUTION_CHECKER: <none / report>,
PROGRESS_TRACKER: <none / set_next_milestone>,
MENTOR: <Engaging_Message>
]
```
 
The process continues based on the student's response, fostering a learn-by-doing environment.
 
The team adhere to the given solution while providing guidance.
 
Scenario: Student has tried to read the solution but didn't get it. Initiate the conversation.
And once the student learn the solution completely the last mentor response should start with "@conclude:<>" marking the end of the conversation.
-
"""
 
_translator_template = """
Translate the following
Content: 
{content}
 
Into {lang}:
"""
 
_format_content_template = """Content:
```
{content}
```
 
Formatted Content:
"""
 
 
def bot_prompt(*, problem: str, solution: str) -> str:
    """Return the formatted bot user-turn prompt."""
    return _bot_init_template.format(problem=problem, solution=solution)
 
 
def translator_prompt(*, content: str, lang: str) -> str:
    """Return the formatted translator user-turn prompt."""
    return _translator_template.format(content=content, lang=lang)
 
 
def format_content_prompt(*, content: str) -> str:
    """Return the formatted content-formatter user-turn prompt."""
    return _format_content_template.format(content=content)