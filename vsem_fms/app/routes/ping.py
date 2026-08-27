from fastapi import APIRouter, status


router = APIRouter(tags=["Ping"])


@router.get(
    "/ping",
    status_code=status.HTTP_200_OK,
    summary="Check server status",
    description="This endpoint allows clients to check if the server is running.",
)
async def ping() -> dict[str, str]:
    """
    Endpoint to check the status of the server.

    Returns:
        dict[str, str]: A dictionary with the status of the server.
    """
    return {"ping": "pong"}
