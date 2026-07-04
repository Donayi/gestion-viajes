from app.bootstrap.app_factory import create_app


app = create_app()


@app.get("/")
def root():
    return {"message": f"{settings.app_name} funcionando"}
