from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN
import numpy as np
from core.database import SessionLocal, Article, Topic 

def run_topic_clustering():
    try:
        model = SentenceTransformer('jhgan/ko-sbert-nli') 
    except Exception as e:
        return 
        
    db = SessionLocal()
    articles_to_cluster = db.query(Article).filter(Article.topic_id == None).limit(100).all()
    
    if len(articles_to_cluster) < 2:
        db.close()
        return

    corpus = [article.title for article in articles_to_cluster] 
    embeddings = model.encode(corpus, show_progress_bar=False) 

    clustering_model = DBSCAN(eps=0.5, min_samples=2, metric='cosine')
    clustering_model.fit(embeddings)
    labels = clustering_model.labels_
    
    num_topics = len(set(labels)) - (1 if -1 in labels else 0)
    
    if num_topics == 0:
        db.close()
        return

    try:
        new_topic_objects = {}
        for topic_label in set(labels):
            if topic_label != -1:
                new_topic = Topic()
                db.add(new_topic)
                new_topic_objects[topic_label] = new_topic
        db.commit()

        for i, article in enumerate(articles_to_cluster):
            label = labels[i]
            if label != -1:
                article.topic_id = new_topic_objects[label].id
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()
        
if __name__ == "__main__":
    run_topic_clustering()