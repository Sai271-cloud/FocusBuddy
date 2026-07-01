```
# Focus Buddy

## Inspiration

I struggle with ADHD, and it's something I have had to face my entire life. I would switch between different productivity tools, plan out my entire day, and still end up not doing my work.

Eventually, I realized that it was less about a more elegant UI or more analytics dashboard; instead, it was about my own accountability. I needed something to help me understand what happened during that focus session. When did I stay on task? When did I drift away? What time of day was I the most focused? What tasks was I the least focused on?

That inspired me to build Focus Buddy: an AI coach that helps students actually track their productivity.

## What it does

### Tracker

Focus Buddy is a productivity tool that helps students start focus sessions and understand how focused they were during that time.

During a session, Focus Buddy classifies the user's time into four states: focused, distracted, uncertain, and away. It does this by using webcam frames together with the task the user is working on. For example, if the task is "read a biology chapter," the AI uses both the webcam frame and the task name/description to decide whether the user appears to be on task.

I also built a browser extension that can optionally give Focus Buddy more context from the active tab. For example, if the task is "write an essay," the extension can share the active website title and URL. This helps the AI make a more accurate prediction because it can compare what the user said they wanted to do with what they are actually doing.

### Session Debrief, Daily Unwind, and Weekly Unwind

Focus Buddy does not just track one session. It also provides long-term analytics and advice.

For the session debrief, Focus Buddy saves the session data and then generates an AI debrief. This debrief explains what happened during the session and gives practical feedback for next time. It points to specific moments from the session instead of giving generic advice.

For example, this is a debrief I recorded while writing the project story:

> You built a solid foundation here by staying locked into your writing for most of the session, even with a few interruptions.
>
> Win: At the 8-minute mark, you successfully navigated away from YouTube and back to Devpost, showing you can steer your attention back when it drifts.
>
> What happened
>
> Your focus was quite resilient, though your attention tended to wander toward YouTube when you were midway through your writing.
>
> Try next time
>
> Since your browser tabs are currently a bit of a pull, you could use a site blocker for the specific duration of your writing session to keep those distractions out of sight.
>
> Your one next step: When you feel the urge to open a new site while writing, commit to writing just one more sentence before switching tabs.

The daily unwind uses information from all the sessions recorded that day to give a general overview of what happened. During each session, the model records important changes in the user's state. For example, if a user shifts from working on an essay to watching YouTube, the model can note that change. These state changes are then used as context for the daily unwind.

The daily unwind also compares the user's focus level for that day with their recent average. For example, if the user's average focus level over the past seven days was 80%, but they recorded 62% today, the model can give encouraging advice while still pointing out the main distractions or struggles from the day.

The weekly unwind works similarly, but it looks at a longer period of time. I also implemented a pattern document that stores general patterns about the user. These patterns can be affirmed or updated by the model after each session. The weekly unwind uses this information to give a recap of the week, including average focus levels, the user's most focused days, and insights into their focus habits.

### Plan Feature

The next feature I built is the plan feature. This allows the user to plan out their day before starting their work. They can pick tasks, schedule them for specific times, estimate how difficult each task will be, and estimate how long each task will take.

Based on this information, the AI can suggest the best times to work on certain tasks using patterns it has learned from the user. This step is completely optional, especially because this feature is still being optimized to provide better suggestions.

The most useful part of the plan feature is that it helps the user compare what they planned with what they actually accomplished. This comparison appears in the daily unwind, where the AI can suggest reducing the workload, adjusting future plans, or encouraging the user to keep going.

### Analytics Page

Focus Buddy also has an analytics page that allows users to look back at their past focus sessions. Users can see their weekly focus percentage, their best days, and their daily and weekly unwinds.

## How we built it

The frontend is built with HTML, CSS, JavaScript, and Tailwind CSS. The frontend handles the task list, focus session timer, webcam preview, live focus chart, analytics page, planning page, and user interface.

The backend is built with FastAPI in Python. It stores tasks, focus sessions, daily plans, analytics data, and AI-generated reflections. I used SQLAlchemy to connect the backend to the database. Locally, the app uses SQLite, and the hosted demo uses Neon Postgres. To improve the tracker's accuracy I also used MediaPipe in order to provide more context to the AI.

For the AI features, I used the Gemini API through the backend. During focus sessions, the frontend sends low-resolution webcam frames, the current task, and optional browser tab context to the backend. Then we get the user's focus state.

I also used Gemini for the debrief and unwind features. After a session, Focus Buddy sends the saved session data to the backend, and Gemini generates a session debrief. The daily and weekly unwinds work in a similar way, but they get context from all the sessions for that given timeframe, as well as the patterns it collects throughout the given time.

For the hosted demo, I deployed the app with Vercel and connected it to Neon Postgres so judges can open the project directly in their browser. For the demo, I listed 5 URLs, each with its own seeded data, so that the judges can experiment with the daily and weekly unwinds.

## Challenges we ran into

One of the biggest challenges that I faced was the AI feedback. At first, the AI feedback was extremely generic, with advice that sounded helpful but wasn't specific to the user. I had to continuously iterate the prompts and provide more context so that the AI could provide good advice. I also forced the AI to follow a consistent template so that it gave more structured feedback with the prompts.

Another challenge I ran into was the focus tracker. A webcam frame by itself is not enough context to accurately determine if someone was focused. For example, if the user's task was reading a book, and they were looking at their screen the whole time, the focus tracker would return the focused state. So, slowly, I had to introduce more and more context in the tracker so that it could accurately get the focus state. Eventually, I incorporated the task name, description, about me section, and optional tab context so the model could effectively determine focus.

Another challenge I ran into was combating the low resolution of the webcams. Since the resolution was so poor, sometimes the model wasn't able to tell whether the person had their eyes open. To combat this, I used MediaPipe. With MediaPipe, I got the face landmarks, and then from there, I checked if the eye was actually open, along with the user's gaze direction and whether the user was present or not. Then I fed the model that information so it could more accurately predict the user's state.

## Accomplishments that we're proud of

For me, the biggest accomplishment I am proud of was creating the focus tracker that worked well. In the beginning, I spent a lot of time trying to get the model to accurately classify the user's state. The model would go through a lot of false positives and false negatives, and eventually, I figured out solutions and workarounds to each issue. To be honest, even if I don't win this hackathon, I feel extremely proud of the fact that I was able to tackle all these different issues and provide a meaningful solution that I believe could significantly benefit many people who struggled with the same issues as me.

## What we learned

I learned many things from this project. This was the first project I officially hosted, so I learned how to deploy a full application and make it available for other people to use. I also learned how to prompt engineer more effectively in order to get better AI responses, as well as how to properly integrate AI into a real project.

On the technical side, I learned how to connect a frontend, backend, and database into one fully working product. I also learned a lot about FastAPI, which I was a complete beginner with before starting this project.

## What's next for Focus Buddy

There are a couple more features I would like to implement for Focus Buddy:

- Building a posture coach alongside a focus coach that helps users correct their posture.
- In this app, I only used the free model of Gemini for the AI features. Later, I want to test out other models and compare their performances in order to provide the best insight possible.
- After a couple more tweaks, I want to try and build this idea into a fully functional website where users can sign up.
- I want to add third-party integrations like Google Calendar to improve the website.
```