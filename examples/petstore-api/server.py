"""FastAPI implementation of the Petstore example service.

This server intentionally keeps all data in memory so it can be started
quickly for demonstrations and automated tests. It exposes a small set
of CRUD operations that align with the bundled OpenAPI specification.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


app = FastAPI(
    title="QA Agent Petstore",
    version="1.0.0",
    description="Sample API used by QA Agent integration tests and docs.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OwnerCreate(BaseModel):
    name: str = Field(..., examples=["Jane Doe"])
    email: Optional[str] = Field(default=None, examples=["jane@example.com"])


class Owner(OwnerCreate):
    id: int = Field(..., examples=[1])


class PetCreate(BaseModel):
    name: str = Field(..., examples=["Fluffy"])
    species: str = Field(..., examples=["cat"])
    age: Optional[int] = Field(default=None, ge=0, examples=[3])
    tags: List[str] = Field(default_factory=list, examples=[["friendly", "therapy"]])
    owner_id: Optional[int] = Field(default=None, examples=[1])


class Pet(PetCreate):
    id: int = Field(..., examples=[1])


PETS: Dict[int, Pet] = {}
OWNERS: Dict[int, Owner] = {}
NEXT_PET_ID = 1
NEXT_OWNER_ID = 1


def _seed_data() -> None:
    global NEXT_OWNER_ID, NEXT_PET_ID

    owner = Owner(id=1, name="Jane Doe", email="jane@example.com")
    OWNERS[owner.id] = owner
    NEXT_OWNER_ID = 2

    pet = Pet(
        id=1,
        name="Milo",
        species="dog",
        age=5,
        tags=["friendly", "vaccinated"],
        owner_id=owner.id,
    )
    PETS[pet.id] = pet
    NEXT_PET_ID = 2


_seed_data()


@app.get("/health", tags=["internal"])
def healthcheck() -> dict[str, str]:
    """Simple health endpoint for smoke tests."""
    return {"status": "ok"}


@app.get("/pets", response_model=List[Pet], tags=["pets"])
def list_pets() -> List[Pet]:
    """Return all pets in the system."""
    return sorted(PETS.values(), key=lambda pet: pet.id)


@app.post(
    "/pets",
    response_model=Pet,
    status_code=status.HTTP_201_CREATED,
    tags=["pets"],
)
def create_pet(payload: PetCreate) -> Pet:
    """Create a new pet."""
    global NEXT_PET_ID

    if payload.owner_id is not None and payload.owner_id not in OWNERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Owner {payload.owner_id} does not exist.",
        )

    pet = Pet(id=NEXT_PET_ID, **payload.model_dump())
    PETS[pet.id] = pet
    NEXT_PET_ID += 1
    return pet


@app.get("/pets/{pet_id}", response_model=Pet, tags=["pets"])
def get_pet(pet_id: int) -> Pet:
    """Retrieve a single pet."""
    pet = PETS.get(pet_id)
    if not pet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found.")
    return pet


@app.put("/pets/{pet_id}", response_model=Pet, tags=["pets"])
def update_pet(pet_id: int, payload: PetCreate) -> Pet:
    """Update an existing pet."""
    if pet_id not in PETS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found.")
    if payload.owner_id is not None and payload.owner_id not in OWNERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Owner {payload.owner_id} does not exist.",
        )
    updated = Pet(id=pet_id, **payload.model_dump())
    PETS[pet_id] = updated
    return updated


@app.delete("/pets/{pet_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["pets"])
def delete_pet(pet_id: int) -> Response:
    """Delete an existing pet."""
    if pet_id not in PETS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found.")
    PETS.pop(pet_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get(
    "/pets/search",
    response_model=List[Pet],
    tags=["pets"],
)
def search_pets(
    tag: Optional[str] = Query(None, description="Tag to match"),
    species: Optional[str] = Query(None, description="Filter by species"),
) -> List[Pet]:
    """Find pets that match tag or species filters."""
    def _matches(pet: Pet) -> bool:
        if tag and tag not in pet.tags:
            return False
        if species and pet.species != species:
            return False
        return True

    return [pet for pet in PETS.values() if _matches(pet)]


@app.get("/owners", response_model=List[Owner], tags=["owners"])
def list_owners() -> List[Owner]:
    """List all owners."""
    return sorted(OWNERS.values(), key=lambda owner: owner.id)


@app.post(
    "/owners",
    response_model=Owner,
    status_code=status.HTTP_201_CREATED,
    tags=["owners"],
)
def create_owner(payload: OwnerCreate) -> Owner:
    """Create a new owner."""
    global NEXT_OWNER_ID
    owner = Owner(id=NEXT_OWNER_ID, **payload.model_dump())
    OWNERS[owner.id] = owner
    NEXT_OWNER_ID += 1
    return owner


@app.get("/owners/{owner_id}", response_model=Owner, tags=["owners"])
def get_owner(owner_id: int) -> Owner:
    """Retrieve owner details."""
    owner = OWNERS.get(owner_id)
    if not owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found.")
    return owner


@app.get("/owners/{owner_id}/pets", response_model=List[Pet], tags=["owners"])
def list_owner_pets(owner_id: int) -> List[Pet]:
    """List pets that belong to the given owner."""
    if owner_id not in OWNERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found.")
    return [pet for pet in PETS.values() if pet.owner_id == owner_id]


@app.get("/stats/species", response_model=Dict[str, int], tags=["analytics"])
def species_counts() -> Dict[str, int]:
    """Aggregate pets by species."""
    counts: Dict[str, int] = {}
    for pet in PETS.values():
        counts[pet.species] = counts.get(pet.species, 0) + 1
    return counts
