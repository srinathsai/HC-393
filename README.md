# HC-393
Graph RAG Experiment


## Steps Of Execution
1) clone this repo to your localhost.
2) Navigate to backend folder and type this command :- docker-compose -f docker-compose-dbs.yml up -d  ( It will activate the redis and neo4j in docker).
3) open new terminal navigate to backend path and type this command :- .venv\Scripts\activate (virtual environment is activated).
4) type :-python clear_databases.py . For making sure db is cleared first .
5) type :- python "path for redis queue.py file after clonning\code_for_clearing_reddis_queue.py" (for clearing the reddis queue).
6) type :- python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000   for running the main server.
7) open new terminal and type :- rq worker construction-queue --url redis://localhost:6379 --worker-class rq.worker.SimpleWorker (for activating redis queue).
8) now after running entire backend open new terminal and type npm install (for activating react components).
9) run npm run dev for ui.

## CLIP(Contrastive Language and Image pretraining) Embedding model :-
1) Core functionality :-
   It has inbuilt 2 transformers called vision transformer and normal transformer for text. Images will have image transformer and text will have embeddings from text encoder . By using contrastive learning CLIP understands the relationship between visual and textual information.  Very advantageous in identifying images based on the text and in situations where images required training under nlp supervision. That is why I have used this embedding and this plays major role in retriving answers related to images.</br>
   ref lin paper :- https://arxiv.org/pdf/2103.00020
