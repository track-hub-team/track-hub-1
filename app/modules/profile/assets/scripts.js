document.addEventListener("DOMContentLoaded", function () {
    console.log("PROFILE REAL SCRIPT LOADED");

    const communitiesList = document.getElementById("followed-communities-list");

    // Leer JSON insertado por backend
    const jsonEl = document.getElementById("followed-communities-json");
    let followedCommunities = [];

    if (jsonEl) {
        followedCommunities = JSON.parse(jsonEl.textContent);
    }

    // Renderizar lista
    if (followedCommunities.length === 0) {
        communitiesList.innerHTML = `<li class="text-muted">You are not following any communities yet.</li>`;
    } else {
        followedCommunities.forEach(comm => {
            const li = document.createElement("li");
            li.classList.add("mb-3");

            li.innerHTML = `
                <a href="/community/${comm.slug}" class="d-flex align-items-center text-decoration-none">
                    <img src="${comm.logo}" class="rounded me-3" style="width:50px;height:50px;object-fit:cover;">
                    <div>
                        <strong>${comm.name}</strong><br>
                        <span class="text-muted small">${comm.description.substring(0, 60)}...</span><br>
                        <span class="badge bg-primary mt-1">${comm.datasets_count} datasets</span>
                    </div>
                </a>
            `;

            communitiesList.appendChild(li);
        });
    }
    // -------------------------------
    // 2. MOCK: Users Followed
    // -------------------------------
    const mockUsers = [
        {
            id: 100,
            name: "Laura",
            surname: "Martinez",
            email: "laura.martinez@example.com",
            affiliation: "University of Barcelona"
        },
        {
            id: 101,
            name: "Carlos",
            surname: "Ruiz",
            email: "cruiz@example.com",
            affiliation: "Data Science Institute"
        },
        {
            id: 102,
            name: "Marta",
            surname: "Lopez",
            email: "marta.lopez@example.com",
            affiliation: "Open Research Labs"
        }
    ];

    const usersList = document.getElementById("followed-users-list");

    mockUsers.forEach(user => {
        const li = document.createElement("li");
        li.classList.add("mb-3");

        li.innerHTML = `
            <div class="d-flex align-items-center justify-content-between">
                <div class="d-flex align-items-center">
                    <div class="rounded-circle bg-secondary text-white d-flex justify-content-center align-items-center me-3"
                         style="width:45px; height:45px; font-size:18px;">
                         ${user.name.charAt(0)}${user.surname.charAt(0)}
                    </div>

                    <div>
                        <strong>${user.name} ${user.surname}</strong><br>
                        <span class="text-muted small">${user.email}</span><br>
                        <span class="small">${user.affiliation}</span>
                    </div>
                </div>

                <!-- Botón UNFOLLOW -->
                <button type="button" class="btn btn-sm btn-danger">
                    Unfollow
                </button>
            </div>
        `;

        usersList.appendChild(li);
    });
});
