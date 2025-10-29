from redis import Redis

# Connect to Redis (use the container name or localhost)
r = Redis(host='localhost', port=6379, decode_responses=True)

# Check current state
print(f"Jobs in queue: {r.llen('rq:queue:construction-queue')}")
print(f"All RQ keys: {len(list(r.scan_iter('rq:*')))}")

# Nuclear clean - delete ALL RQ data
for key in r.scan_iter("rq:*"):
    r.delete(key)
    
print("All RQ data cleared!")

# Verify
print(f"Jobs in queue now: {r.llen('rq:queue:construction-queue')}")
print(f"All RQ keys now: {len(list(r.scan_iter('rq:*')))}")

exit()