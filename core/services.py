import os
import warnings

# Suppress Pydantic V1 warnings from langchain
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")

from dotenv import load_dotenv
from asgiref.sync import sync_to_async
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openrouter import ChatOpenRouter
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field, field_validator
from pypdf import PdfReader
import json
from typing import Any

from .models import UserInfo

load_dotenv()


def get_llm():
    # api_key = os.getenv("OPENROUTER_API_KEY")
    api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
    
    if not api_key:
        raise ValueError("API_KEY is missing")
    # return ChatOpenRouter(
    #     model="openrouter/free",
    #     api_key=api_key,
    #     openrouter_api_key=api_key,
    # )

    return ChatGoogleGenerativeAI(
        model="gemini-3.7-flash",
        api_key=api_key,
    )


class EducationSchema(BaseModel):
    institution: str = Field(default="")
    field: str = Field(default="")
    duration: str = Field(default="")

class ProjectSchema(BaseModel):
    Title: str = Field(default="")
    details: str = Field(default="")
    stack: list[str] = Field(default_factory=list)


class ContactInformationSchema(BaseModel):
    medium: str = Field(default="")
    information: str = Field(default="")



class ResponseSchema(BaseModel):
    full_name: str = Field(default="")
    user_information: str = Field(default="")
    education: list[EducationSchema] = Field(default_factory=list)
    projects: list[ProjectSchema] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    hobbies: list[str] = Field(default_factory=list)
    contact_information: list[ContactInformationSchema] = Field(default_factory=list)

    @field_validator("education", "projects", "contact_information", mode="before")
    @classmethod
    def coerce_to_list(cls, value: Any) -> Any:
        # LLM sometimes returns a single dict instead of a list;
        # normalize to a list so parsing doesn't fail.
        if value is None or value == "":
            return []
        if isinstance(value, dict):
            return [value]
        return value


def _to_prompt_text(value: Any) -> str:
    """Normalize personal_context / past_projects to a clean string for the prompt.

    Accepts str, list, dict, or None (DRF may parse JSON bodies into lists/dicts).
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return str(value)


def extract_text_from_pdf_bytes(data: bytes) -> str:
    """Extract text from an uploaded PDF's raw bytes."""
    from io import BytesIO

    reader = PdfReader(BytesIO(data))
    return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])


# Wrap Django DB operations so they run safely in a thread outside the async event loop
@sync_to_async
def get_existing_profile(user_id: int) -> dict:
    """Fetch the currently saved UserInfo so new info can be merged, not overwritten."""
    try:
        info = UserInfo.objects.get(user_id=user_id)
    except UserInfo.DoesNotExist:
        return {
            "full_name": "",
            "user_information": "",
            "education": [],
            "projects": [],
            "skills": [],
            "hobbies": [],
            "contact_information": [],
        }
    return {
        "full_name": info.full_name or "",
        "user_information": info.user_information or "",
        "education": info.education or [],
        "projects": info.projects or [],
        "skills": info.skills or [],
        "hobbies": info.hobbies or [],
        "contact_information": info.contact_information or [],
    }


def _dedupe_str_list(old: list, new: list) -> list:
    """Union of two string lists, case-insensitive dedupe, order-preserving (old first)."""
    seen = set()
    merged: list[str] = []
    for item in (old or []) + (new or []):
        if not isinstance(item, str):
            item = str(item)
        item = item.strip()
        if not item:
            continue
        key = item.lower()
        if key not in seen:
            seen.add(key)
            merged.append(item)
    return merged


def _dedupe_dict_list(old: list, new: list, key_fn) -> list:
    """Union of two dict lists, deduped by key_fn, order-preserving (old first).

    If the same key appears in both, the NEW entry wins (handles resume updates).
    """
    merged: list[dict] = []
    index_by_key: dict[str, int] = {}
    for item in (old or []) + (new or []):
        if not isinstance(item, dict):
            continue
        key = key_fn(item)
        if not key:
            merged.append(item)
            continue
        if key in index_by_key:
            merged[index_by_key[key]] = item  # new info overwrites same key
        else:
            index_by_key[key] = len(merged)
            merged.append(item)
    return merged


def _education_key(e: dict) -> str:
    return f"{(e.get('institution') or '').strip().lower()}|{(e.get('field') or '').strip().lower()}"


def _project_key(p: dict) -> str:
    return (p.get("Title") or p.get("title") or "").strip().lower()


def _contact_key(c: dict) -> str:
    medium = (c.get("medium") or "").strip().lower()
    if medium:
        return medium
    return (c.get("information") or "").strip().lower()


def _merge_text(old: str, new: str) -> str:
    old, new = (old or "").strip(), (new or "").strip()
    if not new:
        return old
    if not old:
        return new
    if old == new or old in new or new in old:
        return new if len(new) >= len(old) else old
    return f"{old}\n{new}"


def merge_profiles(existing: dict, fresh: dict) -> dict:
    """Deterministic safety-net merge: LLM output merged over existing DB data.

    Scalars keep the new value when present, else the old one. Lists are
    unioned (deduplicated) so adding a single new project/skill never wipes
    what was saved before.
    """
    return {
        "full_name": (fresh.get("full_name") or "").strip() or (existing.get("full_name") or "").strip(),
        "user_information": _merge_text(existing.get("user_information") or "", fresh.get("user_information") or ""),
        "education": _dedupe_dict_list(existing.get("education") or [], fresh.get("education") or [], _education_key),
        "projects": _dedupe_dict_list(existing.get("projects") or [], fresh.get("projects") or [], _project_key),
        "skills": _dedupe_str_list(existing.get("skills") or [], fresh.get("skills") or []),
        "hobbies": _dedupe_str_list(existing.get("hobbies") or [], fresh.get("hobbies") or []),
        "contact_information": _dedupe_dict_list(existing.get("contact_information") or [], fresh.get("contact_information") or [], _contact_key),
    }


@sync_to_async
def save_user_profile(user_id: int, update_data: dict):
    obj, _ = UserInfo.objects.get_or_create(user_id=user_id)
    for field_name, value in update_data.items():
        setattr(obj, field_name, value)
    obj.save(update_fields=list(update_data.keys()))


async def generate_user_information(
    user_id: int,
    personal_context: Any | None = "",
    past_projects: Any | None = "",
    resume_text: Any | None = "",
):
    # Resume text comes ONLY from the user's uploaded file (view-extracted).
    # Never fall back to any bundled file: when the user adds just a single
    # new project/context with no PDF, injecting another resume here would
    # contaminate the prompt and wipe their saved profile.
    resume_text = _to_prompt_text(resume_text)

    if not resume_text.strip() and not _to_prompt_text(personal_context).strip() and not _to_prompt_text(past_projects).strip():
        raise ValueError("Provide personal context, past projects, or upload a resume PDF.")

    # 1. Fetch existing saved profile FIRST so new info is merged, never wipes it.
    existing = await get_existing_profile(user_id)
    existing_text = _to_prompt_text(existing)

    # Normalize new params: view may pass None, list, or dict (JSON body)
    personal_context_text = _to_prompt_text(personal_context)
    past_projects_text = _to_prompt_text(past_projects)
    if not resume_text.strip():
        resume_text = "(no new resume provided)"
    if not personal_context_text.strip():
        personal_context_text = "(no new personal context provided)"
    if not past_projects_text.strip():
        past_projects_text = "(no new past projects provided)"

    parser = PydanticOutputParser(pydantic_object=ResponseSchema)

    prompt = ChatPromptTemplate.from_messages(
        [
           (
    "system",
    """You are an information extraction and profile-generation assistant.

Your task is to conduct an in-depth analysis of the provided resume text, past_project, and personal information to build an extensive, highly detailed structured profile of the user. (your response would be used for a personal ai assistant model)

IMPORTANT — MERGE, DON'T OVERWRITE: an existing saved profile is provided below.
It already contains information the user gave earlier (e.g. old resume, previous projects).
- KEEP every existing fact unless the new input directly contradicts/updates it.
- ADD all new facts (e.g. a newly uploaded resume or a single new project) alongside the old ones.
- DEDUPLICATE: if the same project/skill/education appears in both, keep ONE entry — prefer the NEWER/more detailed version.
- COPY-THROUGH: any section marked "(no new ... provided)" means nothing new for that input — copy the corresponding existing-profile data through unchanged. Never output an empty list/string for a field that has data in the existing profile.
- If a field has no supporting info in EITHER the existing profile or the new input, use "" or [].

Instructions:
1. Thoroughly read and analyze all provided resume content, personal information, and projects information.
2. Extract all available explicit details regarding professional background, technical competencies, soft skills, full employment history, project scope, achievements, technologies used, personal interests, domain expertise, and career trajectory.
3. Extract every contact detail (email, phone, social handles, portfolio/website links) into contact_information as {{medium, information}} pairs — e.g. medium "Email" with the address as information, medium "GitHub" with the profile URL as information.
3. Synthesize information across sources to provide maximum depth within each JSON field. For summaries, project descriptions, and role accomplishments, write rich, multi-sentence contextual breakdowns rather than concise bullet points or surface-level summaries.
4. Interpret and synthesize the facts into structured fields while maintaining strict grounding in the provided sources. Do not simply copy-paste text word-for-word.
5. Strict Factuality: Include ONLY details explicitly supported by the existing profile or the new input text. Do not invent, extrapolate, or infer unmentioned facts.
6. Null Handling: If specific schema fields lack supporting information in BOTH the existing profile and the new input, populate them with an empty string `""` or empty array `[]` as appropriate to the schema.
7. Conflict Resolution: Deduplicate overlapping details. If conflicting timelines or role details appear, prioritize the most recent or granular source (new input wins over old profile).
8. Output Format: Return ONLY a valid JSON object strictly matching the provided schema. Do not include markdown code block formatting (e.g., ```json), intro text, explanations, or commentary.
Response schema:
{response_schema}""",
),
("human", "Existing Saved Profile:\n{existing_profile}\n\nNew Resume:\n{user_input}\n\nNew Personal Context:\n{personal_context}\n\nNew Past Projects:\n {past_projects}"),
    ]).partial(response_schema=parser.get_format_instructions())

   
    # Chain prompt, LLM, and parser directly
    chain = prompt | get_llm() | parser

    # Invoke extraction chain asynchronously
    result = await chain.ainvoke(
        {
            "existing_profile": existing_text,
            "user_input": resume_text,
            "personal_context": personal_context_text,
            "past_projects": past_projects_text,
        }
    )

    # Convert extracted schema to dictionary map, then MERGE with existing
    # (Python-side safety net so nothing saved before is ever lost, even if
    # the LLM drops a field — e.g. user adds just one new project).
    fresh_data = {
        "full_name": result.full_name,
        "user_information": result.user_information,
        "projects": [p.model_dump() for p in result.projects],
        "education": [e.model_dump() for e in result.education],
        "skills": result.skills,
        "hobbies": result.hobbies,
        "contact_information": [c.model_dump() for c in result.contact_information],
    }
    update_data = merge_profiles(existing, fresh_data)

    # Safely execute Django database updates asynchronously
    await save_user_profile(user_id, update_data)
    print("User profile updated successfully!")
