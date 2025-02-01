
// Chat interface styles
const styles = `
  .chat-container {
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
    font-family: sans-serif;
  }
  
  
  .messages {
    height: 500px;
    overflow-y: auto;
    border: 1px solid #ccc;
    padding: 20px;
    margin-bottom: 20px;
  }
  
  .message {
    margin-bottom: 15px;
    display: flex;
  }
  
  .user-message {
    justify-content: flex-end;
  }
  
  .assistant-message {
    justify-content: flex-start;
  }
  
  .message-bubble {
    max-width: 85%;
    padding: 10px 15px;
    border-radius: 15px;
  }
  
  .user-message .message-bubble {
    background: #007bff;
    color: white;
  }
  
  .assistant-message .message-bubble {
    background: #f9f9f9; // #e9ecef;
    color: black;
  }
  
  .input-area {
    display: flex;
    gap: 10px;
  }
  
  .message-input {
    flex-grow: 1;
    padding: 10px;
    max-width: 600px;
    border: 1px solid #ccc;
    border-radius: 5px;
    font-size: 16px;
  }
  
  .send-button {
    padding: 10px 10px;
    background: #007bff;
    color: white;
    border: none;
    border-radius: 5px;
    cursor: pointer;
  }
  
  .send-button:hover {
    background: #0056b3;
  }
`;

// Add styles to document
const styleSheet = document.createElement("style");
styleSheet.textContent = styles;
document.head.appendChild(styleSheet);

// Chat interface class
class ChatInterface {
  constructor() {
    this.messages = [];
    this.prevMessages = [];
    this.createInterface();
    this.bindEvents();
  //  this.sendMessage();
  }

  createInterface() {
    // Get container
    this.container = document.getElementById('chat-container');
    // Create messages area
    this.messagesArea = document.createElement('div');
    this.messagesArea.className = 'messages';

    // Create input area
    this.inputArea = document.createElement('div');
    this.inputArea.className = 'input-area';

    // Create input field
   
    this.input = document.createElement('textarea');
    this.input.className = 'message-input';
    this.input.placeholder = 'Ask a follow up question...';

    // Create send button
    this.sendButton = document.createElement('button');
    this.sendButton.className = 'send-button';
    this.sendButton.textContent = 'Send';

    this.inputArea.innerHTML = "&nbsp;&nbsp;&nbsp;"
    this.inputArea.appendChild(this.input);
    this.inputArea.appendChild(this.sendButton);
    // Assemble the interface
    this.container.appendChild(this.messagesArea);
    this.container.appendChild(this.inputArea);

  }

  bindEvents() {
    // Send message on button click
    this.sendButton.addEventListener('click', () => this.sendMessage(this.input.value));

    // Send message on Enter (but allow Shift+Enter for new lines)
    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });
  }

  sendMessage(query) {
    if (!query) return;
    const message = query.trim();
    if (!message) return;

    // Add user message
    this.addMessage(message, 'user');
    this.input.value = '';

    // Simulate assistant response
    this.getResponse(message);
    this.prevMessages.push(message);
  }

  extractImage(schema_object) {
    if (schema_object && schema_object.image) {
        let image = schema_object.image;
        if (typeof image === 'string') {
                return image;
            } else if (typeof image === 'object' && image.url) {
                return image.url;
            }
        return schema_object.image;
    }
    return null;
  }

  addMessage(content, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    let parsedContent;
    try {
        parsedContent = JSON.parse(content);
    //    console.log(parsedContent);
    } catch (e) {
        parsedContent = content;
    }
    if (Array.isArray(parsedContent)) {
        bubble.innerHTML = parsedContent.map(obj => {
           
            return this.createJsonItemHtml(obj).outerHTML;
        }).join('<br><br>');
    } else {
        bubble.textContent = content;
    }

    messageDiv.appendChild(bubble);
    this.messagesArea.appendChild(messageDiv);
    this.messagesArea.scrollTop = this.messagesArea.scrollHeight;

    this.messages.push({ content, sender });
  }

  htmlUnescape(str) {
    const div = document.createElement("div");
    div.innerHTML = str;
    return div.textContent || div.innerText;
  }
  createJsonItemHtml(item) {
    const container = document.createElement('div');
    container.style.display = 'flex';
    container.style.marginBottom = '1em';
    container.style.gap = '1em';

    // Left content div (title + description)
    const contentDiv = document.createElement('div');
    contentDiv.style.flex = '1';

    // Title row with link and question mark
    const titleRow = document.createElement('div');
    titleRow.style.display = 'flex';
    titleRow.style.alignItems = 'center';
    titleRow.style.gap = '0.5em';
    titleRow.style.marginBottom = '0.5em';

    // Title/link
    const titleLink = document.createElement('a');
    titleLink.href = item.url;
    titleLink.textContent = this.htmlUnescape(`${item.name}`);
    titleLink.style.fontWeight = '600';
    titleLink.style.textDecoration = 'none';
    titleLink.style.color = '#2962ff';
    titleRow.appendChild(titleLink);

    // Question mark icon
    const questionIcon = document.createElement('span');
    questionIcon.innerHTML = '?';
  //  questionIcon.style.cursor = 'help';
    questionIcon.style.fontSize = '0.5em';
    questionIcon.style.position = 'relative';
    
    // Create popup element
    questionIcon.title = item.explanation;
   // questionIcon.style.cursor = 'help';
    titleRow.appendChild(questionIcon);

    contentDiv.appendChild(titleRow);

    // Description
    const description = document.createElement('div');
    description.textContent = item.description;
    description.style.fontSize = '0.9em';
    contentDiv.appendChild(description);

    container.appendChild(contentDiv);

    // Check for image in schema object
    if (item.schema_object) {
        const imgURL = this.extractImage(item.schema_object);
        if (imgURL) {
            const imageDiv = document.createElement('div');
            const img = document.createElement('img');
            img.src = imgURL;
            img.width = 80;
            img.height = 80;
            img.style.objectFit = 'cover';
            imageDiv.appendChild(img);
          container.appendChild(imageDiv);
        }
      } 
    

    return container;
  }

  quickHash(string) {
    let hash = 0;
    for (let i = 0; i < string.length; i++) {
        const char = string.charCodeAt(i);
        hash = (hash << 5) - hash + char;
        hash |= 0; // Convert to 32-bit integer
    }
    return hash;
}

  async getResponse(message) {
    // Add loading state
    const loadingDots = '...';
    this.addMessage(loadingDots, 'assistant');

    try {
      
     // const url = `http://localhost:8080/?query=${encodeURIComponent(message)}&site=seriouseats&prev=${encodeURIComponent(this.prevMessages.join(','))}`;
      const url = `http://74.179.100.160:8080/?query=${encodeURIComponent(message)}&site=seriouseats&prev=${encodeURIComponent(this.prevMessages.join(','))}`;
     console.log(url);
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      const data = await response.json();
      
      // Remove loading message
      this.messagesArea.removeChild(this.messagesArea.lastChild);
      // Add a div with space as content and hash of data as id
      const scrollDiv = document.createElement('span');
      scrollDiv.id = this.quickHash(data.toString());
      scrollDiv.textContent = ' ';
      this.messagesArea.appendChild(scrollDiv);
      
      // Pretty print the JSON response
      const formattedResponse = JSON.stringify(data, null, 2);
      this.addMessage(formattedResponse, 'assistant');
      
      // Scroll back to the div
      scrollDiv.scrollIntoView();
    
    } catch (error) {
      // Remove loading message
      this.messagesArea.removeChild(this.messagesArea.lastChild);
      
      // Show error message
      this.addMessage('Sorry, there was an error connecting to the server.', 'assistant');
      console.error('Error:', error);
    }
  }
}

