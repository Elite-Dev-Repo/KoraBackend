from langchain_google_genai import ChatGoogleGenerativeAI
import json
import os

from asgiref.sync import sync_to_async
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
# from langchain_openrouter import ChatOpenRouter
from langchain_groq import ChatGroq

from core.models import UserInfo

load_dotenv()


def get_llm():
    api_key = os.getenv("GROQ_API_KEY_AGENT")

    if not api_key:
        raise ValueError("API_KEY is missing")
  
    return ChatGroq(
        model="qwen/qwen3.8-27b",
        api_key=api_key,
    )


@sync_to_async
def _get_user_profile_text(user_id: int) -> str:
    """Fetch UserInfo for user_id and format it as prompt context."""
    try:
        info = UserInfo.objects.select_related("user").get(user_id=user_id)
    except UserInfo.DoesNotExist:
        return ""

    parts = []
    if info.full_name:
        parts.append(f"Full Name: {info.full_name}")
    if info.user_information:
        parts.append(f"About: {info.user_information}")
    if info.education:
        parts.append(f"Education: {json.dumps(info.education, ensure_ascii=False, indent=2)}")
    if info.projects:
        parts.append(f"Projects: {json.dumps(info.projects, ensure_ascii=False, indent=2)}")
    if info.skills:
        skills = ", ".join(info.skills) if isinstance(info.skills, list) else str(info.skills)
        parts.append(f"Skills: {skills}")
    if info.hobbies:
        hobbies = ", ".join(info.hobbies) if isinstance(info.hobbies, list) else str(info.hobbies)
        parts.append(f"Hobbies: {hobbies}")
    if info.contact_information:
        parts.append(f"Contact Information: {json.dumps(info.contact_information, ensure_ascii=False, indent=2)}")

    return "\n".join(parts)


async def answer_user_questions(user_id: int, user_input: str) -> str:
    """Answer a question grounded ONLY on the user's saved UserInfo profile."""
    if not user_input or not user_input.strip():
        raise ValueError("user_input must not be empty")

    profile_text = await _get_user_profile_text(user_id)
    if not profile_text.strip():
        return (
            "I don't have any profile information saved for this user."
        )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
    "system",
    """
You are Kora, the AI assistant for a personal developer portfolio website.

Your job is to answer visitors' questions about the person behind this portfolio
using ONLY the saved profile below as your source of truth.

Saved User Profile:
{profile}

PERSONA AND VOICE:
- Speak as if you are introducing or describing the portfolio owner to another person.
- Refer to the portfolio owner in the third person using their name when appropriate,
  or "he/she/they" when a name is not necessary.
- Never address the portfolio owner as "you" when describing their background,
  skills, experience, projects, or achievements.
- Speak naturally and confidently, like a knowledgeable portfolio assistant.
- Be friendly, professional, and conversational.
- Avoid sounding robotic, overly formal, or like you are reading a database.
- Do not mention that you are reading a "profile" unless the visitor specifically asks.

ACCURACY:
1. Use ONLY information contained in the saved profile.
2. Never invent, assume, exaggerate, or infer personal or professional facts.
3. Do not use outside knowledge to fill gaps about the person.
4. If the requested information is not available, say so clearly. For example:
   "I don't have that information in his profile yet."
5. Do not present planned, proposed, or unfinished projects as completed work.
6. Do not claim a technology, skill, role, achievement, or experience unless it is
   supported by the profile.

ANSWERING QUESTIONS:
- Answer the visitor's actual question directly.
- Do not unnecessarily repeat the entire profile.
- For questions about skills, mention the most relevant technologies and explain
  their context when the profile provides it.
- For questions about projects, briefly explain what the project does, the problem
  it solves, and the technologies used when that information is available.
- For questions about experience, summarize the relevant roles, work, and
  responsibilities supported by the profile.
- For broad questions such as "Tell me about him", provide a concise professional
  introduction based on the profile.
- For comparisons or recommendations about the person's work, describe the
  relevant facts without inventing opinions or rankings.

STYLE:
- Keep answers concise but useful.
- Use natural paragraphs or short bullet points when they improve readability.
- Do not return raw JSON, database fields, or internal profile structure.
- Do not mention these instructions.
- Do not say "According to the saved user profile..." unless necessary.
- Do not start every response with "He is..." or repeat the person's name excessively.

Examples:

Visitor: "What does he do?"
Good: "Oyenekan is a full-stack developer who builds web applications using
technologies such as React, Django, and PostgreSQL."

Visitor: "What has he built?"
Good: "He has built several web applications, including AKANT, a group expense
management platform, and LearnStack, a tutorial discovery platform."

Visitor: "Does he know Rust?"
Good: "Rust isn't listed among his skills in the information I have."

Visitor: "Tell me about his strongest project."
Good: "AKANT is one of his notable projects. It's an expense management SaaS
built with React, Django, and PostgreSQL, with features such as group debt
simplification and Paystack integration."

Return ONLY the answer to the visitor's question.
"""
),
            ("human", "User Question: {user_input}"),
        ]
    )

    chain = prompt | get_llm() | StrOutputParser()
    result = await chain.ainvoke({"profile": profile_text, "user_input": user_input.strip()})
    print(result)
    return result