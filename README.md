1.  The microservices in this project communicate using a mix of event-driven messaging and HTTP requests:

    -   Event-driven communication (RabbitMQ)

    -   Services publish events when something significant happens.

    -   Other services subscribe to these events and react accordingly.

    -   Example flow:

        -   auth_service creates a new user → publishes user.created event.

        -   cart_service listens to user.created → creates a shopping cart for the new user.

2.  HTTP communication (httpx)

    -   Some services make direct requests to other services for specific data.

    -   Example flow:

        -   order_service calls cart_service via HTTP to get the user’s cart items when creating an order.

        -   After an order is successfully created, order_service can notify cart_service to clear the purchased items.
