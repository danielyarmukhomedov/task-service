package com.example.taskservice;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.Arrays;
import java.util.List;

@RestController
@RequestMapping("/api/tasks")
public class TaskController {

    @GetMapping
    public List<Task> getTasks() {
        return Arrays.asList(
            new Task(1L, "Изучить Docker", "Написать Dockerfile для Java-приложения", "Высокий"),
            new Task(2L, "Запустить контейнер", "Выполнить сборку и пробросить порты", "Средний"),
            new Task(3L, "Сдать КТ", "Подготовить скриншоты выполнения команд", "Высокий")
        );
    }
}
