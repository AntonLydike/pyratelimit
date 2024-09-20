# Ratelimit - A simple python rate-limiter

## Usage:

```python
# Create a rate-limiter:
from ratelimit import ContinuousLimiter
# generate a ticket every 0.1 seconds
limiter = ContinuousLimiter(0.1)

# use limiter through a context manager: limiter.ticket()
for request in get_all_api_requests_that_need_doing():
    with limiter.ticket():
        do_api_request(request)
```

If you want to allow bursting (i.e. the saving up of tickets when they are not used), you can specify a number of 
`saved_tickets` that can be accrued when the API is not being used.
