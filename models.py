from database import Base
from sqlalchemy import Column, Integer, String, Float

class Recommendations(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    product_description = Column(String)
    product_name = Column(String)
    model_number = Column(String)
    category = Column(String)
    quantity = Column(Integer, nullable=True)
    price = Column(Float, nullable=True)


    def __repr__(self):
        return f"<Recommendation(product_description={self.product_description}, product_name={self.item_id}\
            , model_number={self.model_number}, quantity={self.quantiy}, price={self.price})>"

