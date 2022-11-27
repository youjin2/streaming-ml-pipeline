FROM postgres:12.2

COPY ./sql/* /docker-entrypoint-initdb.d/
CMD ["postgres", "-c", "wal_level=logical"]
