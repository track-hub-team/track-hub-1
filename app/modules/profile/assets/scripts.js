document.addEventListener("DOMContentLoaded", function () {
    console.log("PROFILE MOCK SCRIPT LOADED");

    // -------------------------------
    // 1. MOCK: Communities Followed
    // -------------------------------
    const mockCommunities = [
        {
            id: 1,
            name: "AI Research Hub",
            slug: "ai-research-hub",
            description: "A community focused on Artificial Intelligence datasets.",
            datasets_count: 12,
            logo_path: "/static/img/mock_logo1.png",
            creator: { name: "John", surname: "Doe" }
        },
        {
            id: 2,
            name: "Climate Data Group",
            slug: "climate-data-group",
            description: "Datasets about climate change, environment and sustainability.",
            datasets_count: 8,
            logo_path: "/static/img/mock_logo2.png",
            creator: { name: "Anna", surname: "Smith" }
        }
    ];

    const communitiesList = document.getElementById("followed-communities-list");

    mockCommunities.forEach(comm => {
        const li = document.createElement("li");
        li.classList.add("mb-3");

        li.innerHTML = `
            <div class="d-flex align-items-center justify-content-between">
                <div class="d-flex align-items-center">
                    <img src="${comm.logo_path}"
                         alt="${comm.name}"
                         class="me-3 rounded"
                         style="width:50px; height:50px; object-fit:cover;">

                    <div>
                        <strong>${comm.name}</strong><br>
                        <span class="text-muted small">${comm.description.substring(0, 60)}...</span><br>
                        <span class="badge bg-primary mt-1">${comm.datasets_count} datasets</span><br>
                        <span class="small">Creator: ${comm.creator.name} ${comm.creator.surname}</span>
                    </div>
                </div>

                <!-- Botón UNFOLLOW (solo visual, sin funcionalidad de momento) -->
                <button type="button" class="btn btn-sm btn-danger">
                    Unfollow
                </button>
            </div>
        `;

        communitiesList.appendChild(li);
    });


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
