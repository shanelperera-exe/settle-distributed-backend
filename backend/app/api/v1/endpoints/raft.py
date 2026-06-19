from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any
from app.platform.distributed.raft.node import raft_node

router = APIRouter()

class RequestVotePayload(BaseModel):
    term: int
    candidate_id: str
    last_log_index: int
    last_log_term: int

class AppendEntriesPayload(BaseModel):
    term: int
    leader_id: str
    prev_log_index: int
    prev_log_term: int
    entries: List[Dict[str, Any]]
    leader_commit: int

@router.post("/request_vote")
async def request_vote(payload: RequestVotePayload):
    """
    Raft RequestVote RPC Endpoint.
    Invoked by candidates to gather votes.
    """
    response = await raft_node.handle_request_vote(
        payload.term,
        payload.candidate_id,
        payload.last_log_index,
        payload.last_log_term
    )
    return response

@router.post("/append_entries")
async def append_entries(payload: AppendEntriesPayload):
    """
    Raft AppendEntries RPC Endpoint.
    Invoked by leader to replicate log entries and send heartbeats.
    """
    response = await raft_node.handle_append_entries(
        payload.term,
        payload.leader_id,
        payload.prev_log_index,
        payload.prev_log_term,
        payload.entries,
        payload.leader_commit
    )
    return response
