# TP Integrador: Programación sobre Redes - Chat Multihilo Concurrente

Este proyecto implementa un sistema de chat concurrente Cliente-Servidor estructurado bajo el protocolo de transporte TCP de la capa de transporte utilizando Sockets en Python, hilos avanzados (`threading`) e integración de datos con MySQL Workbench y la API REST de GitHub.

##  Requisitos e Instalación
1. Asegurarse de tener una instancia de **MySQL Workbench** activa en `localhost:3306`.
2. Ejecutar el script SQL provisto en Workbench para estructurar la base de datos `sockets` y las tablas `usuarios`, `repositorios` y `followers`.
3. Instalar las dependencias del proyecto:
   ```bash
   pip install -r requirements.txt