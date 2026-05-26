#!/bin/bash
set -euo pipefail

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

for i in $(seq 1 60); do
    if kafka-topics --bootstrap-server "$KAFKA_BROKER" --list > /dev/null 2>&1; then
        break
    fi
    sleep 2
done

if ! kafka-topics --bootstrap-server "$KAFKA_BROKER" --list > /dev/null 2>&1; then
    exit 1
fi

for TOPIC in "${TOPICS[@]}"; do
    kafka-topics --create \
        --bootstrap-server "$KAFKA_BROKER" \
        --topic "$TOPIC" \
        --partitions "$PARTITIONS" \
        --replication-factor "$REPLICATION" \
        --if-not-exists
done

kafka-topics --bootstrap-server "$KAFKA_BROKER" --list
