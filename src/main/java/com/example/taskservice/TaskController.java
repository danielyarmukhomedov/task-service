package com.example.taskservice;

import java.util.List;
import javax.transaction.Transactional;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/tasks")
public class TaskController {
    private final TaskRepository tasks;

    public TaskController(TaskRepository tasks) { this.tasks = tasks; }

    @GetMapping
    public List<Task> getAllTasks() {
        return tasks.findAll(Sort.by(Sort.Direction.DESC, "id"));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Task createTask(@RequestBody Task input) {
        validate(input);
        Task task = new Task();
        copyDetails(input, task);
        task.setCompleted(false);
        return tasks.save(task);
    }

    @PutMapping("/{id}")
    @Transactional
    public Task updateTask(@PathVariable Long id, @RequestBody Task input) {
        validate(input);
        Task task = find(id);
        copyDetails(input, task);
        return tasks.save(task);
    }

    @PatchMapping("/{id}/completion")
    @Transactional
    public Task setCompletion(@PathVariable Long id, @RequestBody Completion input) {
        if (input.completed == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "completed is required");
        }
        Task task = find(id);
        task.setCompleted(input.completed);
        return tasks.save(task);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    @Transactional
    public void deleteTask(@PathVariable Long id) { tasks.delete(find(id)); }

    private Task find(Long id) {
        return tasks.findById(id).orElseThrow(() ->
                new ResponseStatusException(HttpStatus.NOT_FOUND, "Task not found"));
    }

    private void copyDetails(Task source, Task target) {
        target.setTitle(source.getTitle().trim());
        target.setDescription(source.getDescription() == null ? "" : source.getDescription().trim());
        target.setPriority(source.getPriority());
    }

    private void validate(Task task) {
        if (task.getTitle() == null || task.getTitle().trim().isEmpty()
                || task.getTitle().length() > 255) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "title must contain 1-255 characters");
        }
        if (task.getDescription() != null && task.getDescription().length() > 255) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "description is too long");
        }
        if (!List.of("High", "Medium", "Low").contains(task.getPriority() == null ? "" : task.getPriority())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "priority must be High, Medium or Low");
        }
    }

    public static class Completion {
        public Boolean completed;
    }
}
