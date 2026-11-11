package com.example.taskservice;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest(properties = {
    "spring.datasource.url=jdbc:h2:mem:tasks;MODE=PostgreSQL;DB_CLOSE_DELAY=-1;DB_CLOSE_ON_EXIT=FALSE",
    "spring.datasource.username=sa", "spring.datasource.password=",
    "spring.jpa.properties.hibernate.dialect=org.hibernate.dialect.H2Dialect",
    "spring.jpa.hibernate.ddl-auto=create-drop"
})
@AutoConfigureMockMvc
class TaskApiTest {
    @Autowired MockMvc mvc;
    @Autowired TaskRepository tasks;
    @Autowired ObjectMapper mapper;

    @BeforeEach void clearDatabase() { tasks.deleteAll(); }

    private long create() throws Exception {
        String result = mvc.perform(post("/tasks").contentType(MediaType.APPLICATION_JSON)
            .content("{\"title\":\"Проверка\",\"description\":\"Описание\",\"priority\":\"High\"}"))
            .andExpect(status().isCreated()).andExpect(jsonPath("$.completed").value(false))
            .andReturn().getResponse().getContentAsString();
        return mapper.readTree(result).get("id").asLong();
    }

    @Test void completionIsPersistedAndVisibleOnNextRead() throws Exception {
        long id = create();
        mvc.perform(patch("/tasks/{id}/completion", id).contentType(MediaType.APPLICATION_JSON)
            .content("{\"completed\":true}"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.completed").value(true));
        assertTrue(tasks.findById(id).orElseThrow().isCompleted());
        mvc.perform(get("/tasks")).andExpect(status().isOk())
            .andExpect(jsonPath("$[0].completed").value(true));
        mvc.perform(patch("/tasks/{id}/completion", id).contentType(MediaType.APPLICATION_JSON)
            .content("{\"completed\":false}"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.completed").value(false));
    }

    @Test void invalidInputAndUnknownTaskHaveCorrectStatus() throws Exception {
        mvc.perform(post("/tasks").contentType(MediaType.APPLICATION_JSON)
            .content("{\"title\":\"Title\",\"description\":\"" + "x".repeat(256) + "\",\"priority\":\"High\"}"))
            .andExpect(status().isBadRequest());
        mvc.perform(post("/tasks").contentType(MediaType.APPLICATION_JSON)
            .content("{\"title\":\" \",\"priority\":\"High\"}"))
            .andExpect(status().isBadRequest());
        mvc.perform(post("/tasks").contentType(MediaType.APPLICATION_JSON)
            .content("{\"title\":\"Title\",\"priority\":\"Critical\"}"))
            .andExpect(status().isBadRequest());
        mvc.perform(patch("/tasks/999999/completion").contentType(MediaType.APPLICATION_JSON)
            .content("{\"completed\":true}")).andExpect(status().isNotFound());
        long id = create();
        mvc.perform(patch("/tasks/{id}/completion", id).contentType(MediaType.APPLICATION_JSON)
            .content("{}")).andExpect(status().isBadRequest());
    }

    @Test void deleteRemovesTaskAndRepeatedDeleteReturns404() throws Exception {
        long id = create();
        mvc.perform(delete("/tasks/{id}", id)).andExpect(status().isNoContent());
        assertFalse(tasks.existsById(id));
        mvc.perform(delete("/tasks/{id}", id)).andExpect(status().isNotFound());
    }

    @Test void clientCannotOverwriteExistingIdOnCreate() throws Exception {
        long id = create();
        mvc.perform(post("/tasks").contentType(MediaType.APPLICATION_JSON)
            .content("{\"id\":" + id + ",\"title\":\"Another\",\"priority\":\"Low\",\"completed\":true}"))
            .andExpect(status().isCreated()).andExpect(jsonPath("$.completed").value(false));
        assertEquals(2, tasks.count());
        assertEquals("Проверка", tasks.findById(id).orElseThrow().getTitle());
    }

    @Test void editingDetailsPreservesCompletion() throws Exception {
        long id = create();
        mvc.perform(patch("/tasks/{id}/completion", id).contentType(MediaType.APPLICATION_JSON)
            .content("{\"completed\":true}")).andExpect(status().isOk());
        mvc.perform(put("/tasks/{id}", id).contentType(MediaType.APPLICATION_JSON)
            .content("{\"title\":\"Updated\",\"description\":\"\",\"priority\":\"Low\"}"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.completed").value(true));
    }
}
