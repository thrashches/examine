from sqlalchemy.ext.automap import automap_base
# from sqlalchemy.orm import Session, relationship
from sqlalchemy import create_engine, func
import config


Base = automap_base()

engine = create_engine("mysql+pymysql://{}:{}@{}/{}".format(config.MYSQL_USER, config.MYSQL_PASSWORD,
                                                            config.MYSQL_HOST, config.MYSQL_DATABASE))
Base.prepare(engine, reflect=True)

Genres = Base.classes.genres
Films = Base.classes.films


Posters = Base.classes.posters
Reviews = Base.classes.reviews
Users = Base.classes.users
Roles = Base.classes.roles




