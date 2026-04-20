from pydantic import BaseModel, ConfigDict


class RoleBase(BaseModel):
    nombre: str
    descripcion: str | None = None


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None


class RoleResponse(RoleBase):
    id_rol: int

    model_config = ConfigDict(from_attributes=True)