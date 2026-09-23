from fastapi import FastAPI, Path, Query, Depends, status, Response, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Maps, Base
from utilities import is_valid_url, generate_short_url
from typing import Annotated

app = FastAPI()

# Bind and create tables on startup
Base.metadata.create_all(bind=engine)




# Dependency: Opens a session per request, closes it when done
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()





@app.get("/shortener/{unique}")
def redirect(request: Request, unique :Annotated[str, Path(

    description="Unique 7 character string generated",
    min_length=7,
    max_length=7
    )], db: Session = Depends(get_db)):


    original_long = db.query(Maps).filter(Maps.unique_code == unique).first()

    print("\n\n\n\n\n\n")
    print(original_long.long_url)
    print(type(original_long))
    print("\n\n\n\n\n\n")

    return RedirectResponse(url=original_long.long_url, status_code=302)




@app.post("/shorten", status_code=status.HTTP_201_CREATED)
def shorten(provided_long_url, response: Response, db: Session = Depends(get_db)):

    """We should accept duplicates because if two people in different parts of the world want to shorten the same long URL, you can't say that they can't shorten because someone else has shortened it already"""
    
    # exists = db.query(Maps).filter(Maps.long_url == provided_long_url).first()


    # if exists:
    #     response.status_code = status.HTTP_409_CONFLICT
    #     return {"status":"error", "message":"URL already exists"}
    
    if not is_valid_url(provided_long_url):
        response.status_code = status.HTTP_400_BAD_REQUEST
        
        return {
                "status":"error",
                "message":"Invalid url provided"
                }

    """
    NOW WE HAVE CHECKED FOR ERRORS
    """

    short_url, unique_code = generate_short_url()

    new_url = Maps(
        long_url=provided_long_url,
        shortened_url=short_url,
        unique_code=unique_code,
    )


    db.add(new_url)
    db.commit()
    db.refresh(new_url)


    # Short URL successfully created
    response.status_code = status.HTTP_201_CREATED
    return {
            "long_url":provided_long_url,
            "short_url":short_url,
            "code":unique_code
            }