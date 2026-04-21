#!/bin/bash

KAFKA_BROKER="${KAFKA_BROKER:-kafka:9092}"
PARTITIONS="${PARTITIONS:-3}"
REPLICATION="${REPLICATION:-1}"

TOPICS=(
    "car.events"
    "car.commands"
    "car.location"
    "user.events"
    "user.commands"
    "trip.events"
    "trip.commands"
    "fleet.location.stream"
    "archive.events"
    "car.events.dlt"
    "user.events.dlt"
    "trip.events.dlt"
    "fleet.location.stream.dlt"
)

echo "Waiting for Kafka to be ready..."
for i in $(seq 1 60); do
    if kafka-topics --bootstrap-server "$KAFKA_BROKER" --list > /dev/null 2>&1; then
        echo "Kafka is ready."
        break
    fi
    echo "  attempt $i/60: kafka not ready yet, sleeping 2s..."
    sleep 2
done

if ! kafka-topics --bootstrap-server "$KAFKA_BROKER" --list > /dev/null 2>&1; then
    echo "ERROR: Kafka did not become ready within 120 seconds"
    exit 1
fi

for TOPIC in "${TOPICS[@]}"; do
    echo "Creating topic: $TOPIC"
    kafka-topics --create \
        --bootstrap-server "$KAFKA_BROKER" \
        --topic "$TOPIC" \
        --partitions "$PARTITIONS" \
        --replication-factor "$REPLICATION" \
        --if-not-exists
done

echo "All topics created."
kafka-topics --bootstrap-server "$KAFKA_BROKER" --list
