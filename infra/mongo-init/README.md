# Mongo init (opcional)

Scripts en este directorio se ejecutan al crear la base por primera vez si montas el volumen en el servicio `mongo`:

```yaml
mongo:
  volumes:
    - ./infra/mongo-init:/docker-entrypoint-initdb.d:ro
```

Solo se ejecutan archivos `.js` o `.sh` cuando la base está vacía.
