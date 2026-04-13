# Gunicorn configuration file for the ISMT College RAG Chatbot application
workers = 2
worker_class = "sync"
timeout = 60
keepalive = 5
max_requests = 1000
max_requests_jitter = 50