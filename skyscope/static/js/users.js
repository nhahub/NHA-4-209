const userModal = new bootstrap.Modal(document.getElementById("userModal"));
const passwordModal = new bootstrap.Modal(document.getElementById("passwordModal"));
const usersBody = document.getElementById("usersBody");

document.getElementById("saveUserBtn").addEventListener("click", async () => {
  const payload = {
    username: document.getElementById("newUsername").value,
    full_name: document.getElementById("newFullName").value,
    email: document.getElementById("newEmail").value,
    password: document.getElementById("newPassword").value,
    role: document.getElementById("newRole").value,
  };

  const res = await fetch("/api/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.json();
    alert(err.error || "Failed to create user.");
    return;
  }

  const user = await res.json();
  usersBody.innerHTML += `
    <tr data-user-id="${user.id}">
      <td>${user.id}</td>
      <td><strong>${user.username}</strong></td>
      <td>${user.full_name}</td>
      <td>${user.email}</td>
      <td><span class="role-badge ${user.role.toLowerCase()}">${user.role}</span></td>
      <td>
        <button class="btn btn-sm btn-outline-primary change-pw-btn" data-user-id="${user.id}" data-username="${user.username}">
          <i class="fas fa-key"></i>
        </button>
        <button class="btn btn-sm btn-outline-danger delete-user-btn" data-user-id="${user.id}" data-username="${user.username}">
          <i class="fas fa-trash"></i>
        </button>
      </td>
    </tr>`;

  document.getElementById("userForm").reset();
  userModal.hide();
});

usersBody.addEventListener("click", async (e) => {
  const pwBtn = e.target.closest(".change-pw-btn");
  const delBtn = e.target.closest(".delete-user-btn");

  if (pwBtn) {
    document.getElementById("pwUserId").value = pwBtn.dataset.userId;
    document.getElementById("pwUsername").textContent = pwBtn.dataset.username;
    document.getElementById("newPw").value = "";
    passwordModal.show();
  }

  if (delBtn) {
    if (confirm(`Delete user "${delBtn.dataset.username}"?`)) {
      const res = await fetch(`/api/users/${delBtn.dataset.userId}`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json();
        alert(err.error || "Failed to delete user.");
        return;
      }
      delBtn.closest("tr").remove();
    }
  }
});

document.getElementById("savePwBtn").addEventListener("click", async () => {
  const userId = document.getElementById("pwUserId").value;
  const password = document.getElementById("newPw").value;

  if (!password) {
    alert("Please enter a new password.");
    return;
  }

  const res = await fetch(`/api/users/${userId}/password`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });

  if (res.ok) {
    passwordModal.hide();
    alert("Password updated successfully.");
  } else {
    alert("Failed to update password.");
  }
});
