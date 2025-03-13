const styles = `
  .chat-container {
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
    font-family: sans-serif;
  }
  
  .site-selector {
    margin-bottom: 20px;
  }

  .site-selector select {
    padding: 8px;
    font-size: 14px;
    border-radius: 4px;
    border: 1px solid #ccc;
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
    max-width: 70%;
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
    border: 1px solid #ccc;
    border-radius: 5px;
    font-size: 16px;
  }
  
  .send-button {
    padding: 10px 20px;
    background: #007bff;
    color: white;
    border: none;
    border-radius: 5px;
    cursor: pointer;
  }
  
  .send-button:hover {
    background: #0056b3;
  }

  .intermediate-container {
    padding: 20px 0;
    font-weight: bold;
    font-size: 0.8em;
    color: #333333;
  }
`;

// Add styles to document
const styleSheet = document.createElement("style");
styleSheet.textContent = styles;
document.head.appendChild(styleSheet);

// Chat interface class

class ChatInterface {
    constructor(site=null, model=null) {
        if (site) {
            this.site = site;
        }
        if (model) {
            this.model = model;
        }
    //   console.log("ChatInterface constructor", this.site, this.model);
      this.messages = [];
      this.prevMessages = [];
      this.currentMessage = []
      this.createInterface();
      this.bindEvents();
      this.eventSource = null;
      this.dotsStillThere = false;
    }
  
    makeSelectorLabel(label) {
      const labelDiv = document.createElement('span');
      labelDiv.textContent = " "+ label + " ";
      return labelDiv;
    }

    createSelectors() {
        // Create selectors
      const selector = document.createElement('div');
      this.selector = selector;
      selector.className = 'site-selector';
  
      // Create site selector
      const siteSelect = document.createElement('select');
      this.siteSelect = siteSelect;
      const sites = ['imdb', 'seriouseats', 'npr podcasts', 'backcountry', 'neurips'];
      sites.forEach(site => {
        const option = document.createElement('option');
        option.value = site;
        option.textContent = site;
        siteSelect.appendChild(option);
      });
      this.selector.appendChild(this.makeSelectorLabel("Site"))
      this.selector.appendChild(siteSelect);
      siteSelect.addEventListener('change', () => {
        this.messagesArea.innerHTML = '';
        this.messages = [];
        this.prevMessages = []
      });
  
      // Create model selector
      this.selector.appendChild(this.makeSelectorLabel("Model"))
      const modelSelect = document.createElement('select');
      this.modelSelect = modelSelect;
      const models = ['gpt-4o-mini', 'gpt-4o', 'gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash-exp'];
      models.forEach(model => {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model;
        modelSelect.appendChild(option);
      });
     
      this.selector.appendChild(modelSelect);
      modelSelect.addEventListener('change', () => {
        this.messagesArea.innerHTML = '';
        this.messages = [];
        this.prevMessages = []
      });
  
      this.container.appendChild(this.selector);
    }
  
    createInterface() {
      // Create main container
      this.container = document.getElementById('chat-container');

  
      if (!this.site || !this.model) {
        this.createSelectors();
      }
      // Create messages area
      this.messagesArea = document.createElement('div');
      this.messagesArea.className = 'messages';
  
      // Create input area
      this.inputArea = document.createElement('div');
      this.inputArea.className = 'input-area';
  
      // Create input field
      this.input = document.createElement('textarea');
      this.input.className = 'message-input';
      this.input.placeholder = 'Type your message...';
  
      // Create send button
      this.sendButton = document.createElement('button');
      this.sendButton.className = 'send-button';
      this.sendButton.textContent = 'Send';
  
      // Assemble the interface
      this.inputArea.appendChild(this.input);
      this.inputArea.appendChild(this.sendButton);
      this.container.appendChild(this.messagesArea);
      this.container.appendChild(this.inputArea);
  
      // Add to document
     // document.body.appendChild(this.container);
    }
  
    bindEvents() {
      // Send message on button click
      this.sendButton.addEventListener('click', () => this.sendMessage());
  
      // Send message on Enter (but allow Shift+Enter for new lines)
      this.input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });
    }
  
    sendMessage(query=null) {
      const message = query || this.input.value.trim();
      if (!message) return;
  
      // Add user message
      this.addMessage(message, 'user');
      this.currentMessage = message;
      this.input.value = '';
  
      // Simulate assistant response
      this.getResponse(message);
    }
  
    extractImage(schema_object) {
      if (schema_object && schema_object.image) {
          let image = schema_object.image;
          if (typeof image === 'string') {
              return image;
          } else if (typeof image === 'object' && image.url) {
              return image.url;
          } else if (image instanceof Array) {
              return image[0];
          }
          return schema_object.image;
      }
      return null;
    }
  
    htmlUnescape(str) {
    const div = document.createElement("div");
    div.innerHTML = str;
    return div.textContent || div.innerText;
    }
  
    addMessage(content, sender) {
      const messageDiv = document.createElement('div');
      messageDiv.className = `message ${sender}-message`;
  
      const bubble = document.createElement('div');
      bubble.className = 'message-bubble';
      let parsedContent;
      try {
          parsedContent = JSON.parse(content);
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
     
      this.currentMessage = "";
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
     // this.currentMessage.push([item.url, item.name, item.description]);
  
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
  
    getAndProcessResponse(url) {
      this.eventSource = new EventSource(url);
      this.eventSource.chatInterface = this;
      this.eventSource.onopen = function(event) {
      }
      this.eventSource.onmessage = function(event) {
        const chatInterface = this.chatInterface;
        if (chatInterface.dotsStillThere) {
          this.scrollDiv = chatInterface.handleFirstMessage(event);
          const messageDiv = document.createElement('div');
          messageDiv.className = `message assistant-message`;
          const bubble = document.createElement('div'); 
          bubble.className = 'message-bubble';
          messageDiv.appendChild(bubble);
          chatInterface.bubble = bubble;
          chatInterface.messagesArea.appendChild(messageDiv);
        }
        const data = JSON.parse(event.data);
        console.log("data", data);
        if (data && data.message_type == "answer") {
            chatInterface.bubble.appendChild(chatInterface.createJsonItemHtml(data));
        } else if (data && data.message_type == "result_batch") {
          for (const item of data.results) {
            chatInterface.bubble.appendChild(chatInterface.createJsonItemHtml(item));
          }
        } else if (data && data.message_type == "poor_results") {
          chatInterface.bubble.appendChild(chatInterface.createPoorResultsHtml());
        } else if (data && data.message_type == "insufficient_results") {
          chatInterface.bubble.appendChild(chatInterface.createInsufficientResultsHtml());
        } else if (data && data.message_type == "complete") {
          this.scrollDiv.scrollIntoView();
          this.close();
        }
      }
   }
  
    createPoorResultsHtml() {
      const container = document.createElement('div');
      container.className = 'intermediate-container';
      container.appendChild(document.createElement('br'));
      container.appendChild(document.createElement('br'));
      container.textContent = "The following results might not be that relevant to your query, but you might find them useful.";
      container.appendChild(document.createElement('br'));
      container.appendChild(document.createElement('br'));
      container.appendChild(document.createElement('br'));

      return container;
    }
  
    createInsufficientResultsHtml() {
      const container = document.createElement('div');
      container.className = 'intermediate-container';
      container.appendChild(document.createElement('br'));

      container.textContent = "I couldn't find any more results that are relevant to your query.";
      container.appendChild(document.createElement('br'));
      return container;
    }
  
    handleFirstMessage(event) {
      this.dotsStillThere = false;
      this.messagesArea.removeChild(this.messagesArea.lastChild);
      const scrollDiv = document.createElement('span');
      scrollDiv.id = this.quickHash(event.data.toString());
      scrollDiv.textContent = ' ';
      this.messagesArea.appendChild(scrollDiv);
      return scrollDiv;
    }
  
    async getResponse(message) {
      // Add loading state
      const loadingDots = '...';
      this.addMessage(loadingDots, 'assistant');
      this.dotsStillThere = true;
  
      try {
        const selectedSite = (this.site ||this.siteSelect.value);
        const selectedModel = (this.model || this.modelSelect.value);
        const prev = encodeURIComponent(JSON.stringify(this.prevMessages));
        const host = "http://localhost:8000";
        const remoteHost = "http://74.179.100.160:8000";
        const queryString = `query=${encodeURIComponent(message)}&site=${encodeURIComponent(selectedSite)}&model=${encodeURIComponent(selectedModel)}&prev=${prev}`;
        const url = `${remoteHost}/?${queryString}`;
       // const url = `${host}/?${queryString}`;
        console.log("url", url);
        this.getAndProcessResponse(url);
        this.prevMessages.push(message);
        return
      } catch (error) {
        console.error('Error fetching response:', error);
      }
    }
  }
  