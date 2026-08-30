from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from api_parser.parser import APIParser
from api_parser.schemas import NormalizedAPISpec

router = APIRouter()
parser_instance = APIParser()


class ParseDocRequest(BaseModel):
    url: str = Field(description="URL or raw text/JSON/YAML of the API documentation")


@router.get("/status")
def status():
    return {"status": "ok"}


@router.post("/parse-doc", response_model=NormalizedAPISpec)
async def parse_documentation(request: ParseDocRequest):
    """
    Ingests and parses API documentation from a URL or raw content string.
    Returns a normalized structured API specification.
    """
    if not request.url or not request.url.strip():
        raise HTTPException(status_code=400, detail="Documentation URL or content cannot be empty.")

    try:
        spec = await parser_instance.parse_doc(request.url)
        return spec
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process documentation: {str(exc)}")
