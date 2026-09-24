FROM eclipse-temurin:11-jdk-alpine
WORKDIR /app
COPY target/task-service-1.0.0.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
