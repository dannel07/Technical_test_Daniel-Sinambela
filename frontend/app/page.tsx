'use client';

import { useEffect, useMemo, useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8010';

interface User {
  id: number;
  username: string;
  name: string;
  email: string;
}

interface Task {
  id: number;
  title: string;
  description?: string;
  status: string;
  deadline: string;
  assignee_id?: number;
  assignee?: User;
}

function statusClass(status: string) {
  switch (status) {
    case 'Done':
      return 'status-done';
    case 'In Progress':
      return 'status-progress';
    default:
      return 'status-todo';
  }
}

export default function HomePage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [token, setToken] = useState('');
  const [loggedIn, setLoggedIn] = useState(false);
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('password123');
  const [form, setForm] = useState({ title: '', description: '', status: 'Todo', deadline: '', assignee_id: '' });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [message, setMessage] = useState('');
  const [chatInput, setChatInput] = useState('');
  const [chatReply, setChatReply] = useState('');
  const [chatError, setChatError] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [loading, setLoading] = useState(false);

  const stats = useMemo(() => {
    const todo = tasks.filter((task) => task.status === 'Todo').length;
    const inProgress = tasks.filter((task) => task.status === 'In Progress').length;
    const done = tasks.filter((task) => task.status === 'Done').length;
    return { todo, inProgress, done };
  }, [tasks]);

  async function login(e?: React.FormEvent) {
    e?.preventDefault();
    try {
      setLoading(true);
      setMessage('');
      const res = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Login failed');
      setToken(data.access_token);
      setLoggedIn(true);
      await loadData(data.access_token);
    } catch (error) {
      setLoggedIn(false);
      setMessage(error instanceof Error ? error.message : 'Unexpected error');
    } finally {
      setLoading(false);
    }
  }

  async function loadData(accessToken: string) {
    const [tasksRes, usersRes] = await Promise.all([
      fetch(`${API_URL}/tasks`, { headers: { Authorization: `Bearer ${accessToken}` } }),
      fetch(`${API_URL}/users`, { headers: { Authorization: `Bearer ${accessToken}` } }),
    ]);
    const tasksData = await tasksRes.json();
    const usersData = await usersRes.json();
    setTasks(tasksData);
    setUsers(usersData);
  }

  async function saveTask(e: React.FormEvent) {
    e.preventDefault();
    const payload = {
      title: form.title,
      description: form.description,
      status: form.status,
      deadline: form.deadline,
      assignee_id: form.assignee_id ? Number(form.assignee_id) : null,
    };

    const url = editingId ? `${API_URL}/tasks/${editingId}` : `${API_URL}/tasks`;
    const method = editingId ? 'PUT' : 'POST';
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      setMessage(editingId ? 'Task updated successfully.' : 'Task created successfully.');
      setForm({ title: '', description: '', status: 'Todo', deadline: '', assignee_id: '' });
      setEditingId(null);
      await login();
    }
  }

  async function deleteTask(id: number) {
    const res = await fetch(`${API_URL}/tasks/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
    if (res.ok) {
      setMessage('Task deleted.');
      await login();
    }
  }

  async function updateStatus(id: number, status: string) {
    const res = await fetch(`${API_URL}/tasks/${id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ status }),
    });
    if (res.ok) {
      setMessage('Status updated.');
      await login();
    }
  }

  async function askAi() {
    const messageText = chatInput.trim();
    if (!messageText) {
      setChatError('Silakan ketik pertanyaan terlebih dahulu.');
      return;
    }

    setChatLoading(true);
    setChatError('');
    setChatReply('');
    try {
      const res = await fetch(`${API_URL}/ai/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ message: messageText }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'AI request failed');
      setChatReply(data.reply || 'Saya tidak mendapatkan respons.');
      setChatInput('');
    } catch (error) {
      setChatError(error instanceof Error ? error.message : 'Unexpected error');
    } finally {
      setChatLoading(false);
    }
  }

  function editTask(task: Task) {
    setEditingId(task.id);
    setForm({
      title: task.title,
      description: task.description || '',
      status: task.status,
      deadline: task.deadline,
      assignee_id: task.assignee_id ? String(task.assignee_id) : '',
    });
  }

  if (!loggedIn) {
    return (
      <main className="app-shell login-shell">
        <section className="panel-card login-card">
          <h1>Task Management Studio</h1>
          <p className="muted">Masuk untuk mengelola task Anda.</p>
          {message ? <p className="notice">{message}</p> : null}
          <form onSubmit={(e) => void login(e)} className="form-stack">
            <input placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} required />
            <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            <button type="submit" className="primary-btn" disabled={loading}>
              {loading ? 'Signing in...' : 'Login'}
            </button>
          </form>
          <p className="muted small-text">Demo login: admin / password123</p>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <section className="hero-card">
        <div>
          
          <h1>Task Management Studio</h1>
          <p className="hero-text">Kelola pekerjaan lebih rapi, pantau progres, dan gunakan asisten AI untuk cepat mendapatkan insight penting.</p>
        </div>
        <div className="stats-grid">
          <div className="stat-card">
            <strong>{tasks.length}</strong>
            <span>Total tasks</span>
          </div>
          <div className="stat-card">
            <strong>{stats.todo}</strong>
            <span>Todo</span>
          </div>
          <div className="stat-card">
            <strong>{stats.inProgress}</strong>
            <span>In progress</span>
          </div>
          <div className="stat-card">
            <strong>{stats.done}</strong>
            <span>Done</span>
          </div>
        </div>
      </section>

      {message ? <p className="notice">{message}</p> : null}

      <section className="grid-layout">
        <div className="panel-card">
          <h2>{editingId ? 'Edit task' : 'Create task'}</h2>
          <form onSubmit={saveTask} className="form-stack">
            <input placeholder="Task title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
            <textarea placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} />
            <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option value="Todo">Todo</option>
              <option value="In Progress">In Progress</option>
              <option value="Done">Done</option>
            </select>
            <input type="date" value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })} required />
            <select value={form.assignee_id} onChange={(e) => setForm({ ...form, assignee_id: e.target.value })}>
              <option value="">Select assignee</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>{user.name}</option>
              ))}
            </select>
            <button type="submit" className="primary-btn">{editingId ? 'Update task' : 'Add task'}</button>
          </form>
        </div>

        <div className="panel-card">
          <h2>AI assistant</h2>
          <p className="muted">Coba pertanyaan yang lebih natural seperti:</p>
          <ul className="prompt-list">
            <p>“Tampilkan semua task yang belum selesai”</p>
            <p>“Berapa jumlah task yang sudah selesai?”</p>
            <p>“Tugas apa saja yang deadline-nya hari ini?”</p>
            <p>“Siapa assignee dari task Design review?”</p>
          </ul>
          <div className="chat-box">
            <textarea value={chatInput} onChange={(e) => setChatInput(e.target.value)} placeholder="Tanya asisten tentang task Anda..." rows={4} />
            <button className="primary-btn" onClick={askAi} disabled={chatLoading}>
              {chatLoading ? 'Memproses...' : 'Ask AI'}
            </button>
            {chatError ? <div className="reply-box error-box">{chatError}</div> : null}
            {chatReply ? <div className="reply-box"><strong>Jawaban AI</strong>
              <div>{chatReply}</div></div> : null}
          </div>
        </div>
      </section>

      <section className="task-list">
        {tasks.map((task) => (
          <article key={task.id} className={`task-card ${statusClass(task.status)}`}>
            <div>
              <h3>{task.title}</h3>
              <p>{task.description}</p>
            </div>
            <div className="task-meta">
              <span className={`pill ${statusClass(task.status)}`}>{task.status}</span>
              <span>Deadline: {task.deadline}</span>
              <span>Assignee: {task.assignee?.name || 'Unassigned'}</span>
            </div>
            <div className="task-actions">
              <button className="ghost-btn" onClick={() => editTask(task)}>Edit</button>
              <button className="ghost-btn" onClick={() => deleteTask(task.id)}>Delete</button>
              <select value={task.status} onChange={(e) => updateStatus(task.id, e.target.value)}>
                <option value="Todo">Todo</option>
                <option value="In Progress">In Progress</option>
                <option value="Done">Done</option>
              </select>
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}
