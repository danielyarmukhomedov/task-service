package com.example.taskservice;

public class Task {
    private Long id;
    private String title;
    private String description;
    private String priority;

    public Task(Long id, String title, String description, String priority) {
        this.id = id;
        this.title = title;
        this.description = description;
        this.priority = priority;
    }

    public Long getId() { return id; }
    public String getTitle() { return title; }
    public String getDescription() { return description; }
    public String getPriority() { return priority; }
}
