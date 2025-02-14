const styles = `
  .chat-container {
  /*  max-width: 600px;
    max-height: 600px; */
    height: 80%;
    width: 80%;
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
   /* max-height: 500px;
    max-width: 500px; */
    height: 80%;
    width: 80%;
    overflow-y: auto;
    border: 1px solid #ccc;
    padding: 20px;
    margin-bottom: 2px;
  }

   .messages_full {
   /* max-height: 500px;
    max-width: 500px; */
    height: 95%;
    width: 100%;
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

  .remember-message {
    font-weight: bold;
  /  font-size: 0.8em;
    color: #333333;
    justify-content: flex-start;
    margin-bottom: 1em;
  }

  .item-detail-message {
    font-size: 0.9em;
    color: #333333;
    justify-content: flex-start;
   / margin-bottom: 0.5em;
  }
  
  .message-bubble {
    max-width: 90%;
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
    width: 87%;
  }

   .input-area_full {
    display: flex;
    gap: 10px;
    width: 100%;
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

class ManagedEventSource {
  constructor(url, options = {}) {
    this.url = url;
    this.options = options;
    this.maxRetries = options.maxRetries || 3;
    this.retryCount = 0;
    this.eventSource = null;
    this.isStopped = false;
  }

  connect(chatInterface) {
    if (this.isStopped) {
      return;
    }
    this.eventSource = new EventSource(this.url);
    this.eventSource.chatInterface = chatInterface;
    this.eventSource.onopen = () => {
    //  console.log('Connection established');
      this.retryCount = 0; // Reset retry count on successful connection
    };

    this.eventSource.onerror = (error) => {
      if (this.eventSource.readyState === EventSource.CLOSED) {
        console.log('Connection was closed');
        
        if (this.retryCount < this.maxRetries) {
          this.retryCount++;
          console.log(`Retry attempt ${this.retryCount} of ${this.maxRetries}`);
          
          // Implement exponential backoff
          const backoffTime = Math.min(1000 * Math.pow(2, this.retryCount), 10000);
          setTimeout(() => this.connect(), backoffTime);
        } else {
          console.log('Max retries reached, stopping reconnection attempts');
          this.stop();
        }
      }
    }

    this.eventSource.onmessage = function(event) {
      if (this.chatInterface.dotsStillThere) {
        this.chatInterface.handleFirstMessage(event);
        const messageDiv = document.createElement('div');
        messageDiv.className = `message assistant-message`;
        const bubble = document.createElement('div'); 
        bubble.className = 'message-bubble';
        messageDiv.appendChild(bubble);
        this.chatInterface.bubble = bubble;
        this.chatInterface.messagesArea.appendChild(messageDiv);
        this.chatInterface.currentItems = []
        this.chatInterface.thisRoundRemembered = null;
      }
      const data = JSON.parse(event.data);
      if (data && data.message_type == "query_analysis") {
        this.chatInterface.itemToRemember.push(data.item_to_remember);
        this.chatInterface.decontextualizedQuery = data.decontextualized_query;
        this.chatInterface.possiblyAnnotateUserQuery(this.chatInterface, data.decontextualized_query);
        if (this.chatInterface.itemToRemember) {
          this.chatInterface.memoryMessage(data.item_to_remember, this.chatInterface)
        }
      } else if (data && data.message_type == "remember") {
        this.chatInterface.memoryMessage(data.message, this.chatInterface)          
      } else if (data && data.message_type == "result_batch") {
        for (const item of data.results) {
          const domItem = this.chatInterface.createJsonItemHtml(item)
          this.chatInterface.currentItems.push([item, domItem])
          this.chatInterface.bubble.appendChild(domItem);
          this.chatInterface.num_results_sent++;
        }
        this.chatInterface.resortResults(this.chatInterface);
      } else if (data && data.message_type == "intermediate_message") {
        this.chatInterface.bubble.appendChild(this.chatInterface.createIntermediateMessageHtml(data.message));
      } else if (data && data.message_type == "complete") {
        this.chatInterface.resortResults(this.chatInterface);
        this.chatInterface.scrollDiv.scrollIntoView();
        this.close();
      }
    }
  }
      

  stop() {
    this.isStopped = true;
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  // Method to manually reset and reconnect
  reset() {
    this.retryCount = 0;
    this.isStopped = false;
    this.stop();
    this.connect();
  }
};

// Usage example:
const eventSourceOptions = {
  maxRetries: 3,
  eventListeners: {
    message: (event) => console.log('Received message:', event.data),
    customEvent: (event) => console.log('Custom event:', event.data)
  }
};

//const source = new ManagedEventSource('/api/events', eventSourceOptions);
//source.connect();

// To stop the connection:
// source.stop();

// To reset and reconnect:
// source.reset();



// Chat interface class

class ChatInterface {
    constructor(site=null, model=null, mode="dropdown") {
        if (site) {
            this.site = site;
        }
        if (model) {
            this.model = model;
        }
        
        // Parse URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        const query = urlParams.get('query');
        const urlModel = urlParams.get('model');
        const prevMessagesStr = urlParams.get('prev');
        
        if (urlModel) {
            this.model = urlModel;
        }
        
        this.mode = mode;
        this.messages = [];
        this.prevMessages = prevMessagesStr ? JSON.parse(decodeURIComponent(prevMessagesStr)) : [];
        this.currentMessage = [];
        this.currentItems = [];
        this.itemToRemember = [];
        this.createInterface(mode);
        this.bindEvents();
        this.eventSource = null;
        this.dotsStillThere = false;

        // Add message if query parameter exists
        if (query) {
            this.sendMessage(decodeURIComponent(query));
        }
    }
  
    makeSelectorLabel(label) {
      const labelDiv = document.createElement('span');
      labelDiv.textContent = " "+ label + " ";
      return labelDiv;
    }

    sites () {
      return ['imdb', 'seriouseats', 'npr podcasts', 'backcountry', 'neurips', 'zillow',
      'tripadvisor', 'woksoflife', 'cheftariq', 'hebbarskitchen', 'latam_recipes', 'spruce', 'all'];
    }
    createSelectors() {
        // Create selectors
      const selector = document.createElement('div');
      this.selector = selector;
      selector.className = 'site-selector';
  
      // Create site selector
      const siteSelect = document.createElement('select');
      this.siteSelect = siteSelect;
      this.sites().forEach(site => {
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
      const models = ['gpt-4o-mini', 'gpt-4o', 'gemini-1.5-flash', 
        'gemini-1.5-pro', 'gemini-2.0-flash-exp', 
        'claude-3-5-sonnet-latest', 'claude-3-5-haiku-latest'];
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
  
      // Create clear chat icon
      const clearIcon = document.createElement('span');
      clearIcon.innerHTML = '<img src="/html/clear.jpeg" width="16" height="16" style="vertical-align: middle; cursor: pointer; margin-left: 8px;">';
      clearIcon.title = "Clear chat history";
      clearIcon.addEventListener('click', () => {
        this.messagesArea.innerHTML = '';
        this.messages = [];
        this.prevMessages = [];
      });
      this.selector.appendChild(clearIcon);

      this.container.appendChild(this.selector);
    }
  
    createInterface(mode="dropdown") {
      // Create main container
      this.container = document.getElementById('chat-container');

      if (mode == "dropdown") {
        this.createSelectors();
      }
      // Create messages area
      
      this.messagesArea = document.createElement('div');
      this.messagesArea.className = (mode == "dropdown" ? 'messages' : 'messages_full');
      
      // Create input area
      this.inputArea = document.createElement('div');
      this.inputArea.className = (mode == "dropdown" ? 'input-area' : 'input-area_full');
  
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
      if (sender == "user") {
        this.lastUserMessageDiv = messageDiv;
        const scrollDiv = document.createElement('span');
        scrollDiv.id = this.quickHash(content.toString());
        messageDiv.appendChild(scrollDiv);
        messageDiv.appendChild(document.createElement('br'));
        messageDiv.appendChild(document.createElement('br'));
        this.scrollDiv = scrollDiv;
      }
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

    makeAsDiv(content) {
      const div = document.createElement('div');
      div.className = 'item-detail-message';
      div.textContent = content;
      return div;
    }

    typeSpecificContent(item, contentDiv) {
      const houseTypes = ["SingleFamilyResidence", "Apartment", "Townhouse", "House", "Condominium", "RealEstateListing"]
    //  console.log(item.schema_object['@type'])
      if (item.schema_object && houseTypes.includes(item.schema_object['@type'])) {
        const price = item.schema_object.price;
        const address = item.schema_object.address;
        const numBedrooms = item.schema_object.numberOfRooms;
        const numBathrooms = item.schema_object.numberOfBathroomsTotal;
        const sqft = item.schema_object.floorSize.value;
        let priceValue = price;
        if (typeof price === 'object') {
          priceValue = price.price || price.value || price;
          priceValue = Math.round(priceValue / 100000) * 100000;
          priceValue = priceValue.toLocaleString('en-US');
        }
        contentDiv.appendChild(document.createElement('br'));
        contentDiv.appendChild(this.makeAsDiv(address.streetAddress + ", " + address.addressLocality))
        contentDiv.appendChild(this.makeAsDiv(`${numBedrooms} bedrooms, ${numBathrooms} bathrooms, ${sqft} sqft`))
        contentDiv.appendChild(this.makeAsDiv(`Listed at ${priceValue}`))
        
      }
    }

    clearHistory() {
      this.messagesArea.innerHTML = "";
      this.messages = [];
      this.prevMessages = [];
    }
  
    getItemName(item) {
      if (item.name) {
        return item.name;
      } else if (item.schema_object && item.schema_object.keywords) {
        return item.schema_object.keywords;
      }
      return item.url;
    }

    createJsonItemHtml(item) {
    //  console.log("createJsonItemHtml", item);
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
      const itemName = this.getItemName(item);
      titleLink.textContent = this.htmlUnescape(`${itemName}`);
      titleLink.style.fontWeight = '600';
      titleLink.style.textDecoration = 'none';
      titleLink.style.color = '#2962ff';
      titleRow.appendChild(titleLink);
  
      // info icon
      const infoIcon = document.createElement('span');
      infoIcon.innerHTML = '<img src="/html/info.png" width="16" height="16">';
    //  questionIcon.style.cursor = 'help';
      infoIcon.style.fontSize = '0.5em';
      infoIcon.style.position = 'relative';
      
      
      // Create popup element
      infoIcon.title = item.explanation + "(" + item.score + ")";
     // questionIcon.style.cursor = 'help';
      titleRow.appendChild(infoIcon);
  
      contentDiv.appendChild(titleRow);
  
      // Description
      const description = document.createElement('div');
      description.textContent = item.description;
      description.style.fontSize = '0.9em';
      contentDiv.appendChild(description);

      if (this.mode == "nlwebsearch") {
          // visible url
          const visibleUrl = document.createElement("div");
          const visibleUrlLink = document.createElement("a");
          visibleUrlLink.href = item.siteUrl;
          visibleUrlLink.textContent = item.site;
          visibleUrlLink.style.fontSize = "0.9em";
          visibleUrlLink.style.textDecoration = "none";
          visibleUrlLink.style.color = "#2962ff";
          visibleUrlLink.style.fontWeight = "500";
          visibleUrlLink.style.padding = "8px 0";
          visibleUrlLink.style.display = "inline-block";
          contentDiv.appendChild(visibleUrlLink);
      }

      this.typeSpecificContent(item, contentDiv);

      // Feedback icons
      const feedbackDiv = document.createElement('div');
      feedbackDiv.style.display = 'flex';
      feedbackDiv.style.gap = '0.5em';
      feedbackDiv.style.marginTop = '0.5em';

      const thumbsUp = document.createElement('span');
      thumbsUp.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="#D3D3D3">
        <path d="M2 20h2c.55 0 1-.45 1-1v-9c0-.55-.45-1-1-1H2v11zm19.83-7.12c.11-.25.17-.52.17-.8V11c0-1.1-.9-2-2-2h-5.5l.92-4.65c.05-.22.02-.46-.08-.66-.23-.45-.52-.86-.88-1.22L14 2 7.59 8.41C7.21 8.79 7 9.3 7 9.83v7.84C7 18.95 8.05 20 9.34 20h8.11c.7 0 1.36-.37 1.72-.97l2.66-6.15z"/>
      </svg>`;
      thumbsUp.style.fontSize = '0.8em';
      thumbsUp.style.cursor = 'pointer';

      const thumbsDown = document.createElement('span');
      thumbsDown.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="#D3D3D3">
        <path d="M15 3H6c-.83 0-1.54.5-1.84 1.22l-3.02 7.05c-.09.23-.14.47-.14.73v2c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L9.83 23l6.59-6.59c.36-.36.58-.86.58-1.41V5c0-1.1-.9-2-2-2zm4 0v12h4V3h-4z"/>
      </svg>`;
      thumbsDown.style.fontSize = '0.8em'; 
      thumbsDown.style.cursor = 'pointer';

      feedbackDiv.appendChild(thumbsUp);
      feedbackDiv.appendChild(thumbsDown);
      contentDiv.appendChild(feedbackDiv);
  
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

   possiblyAnnotateUserQuery(chatInterface, decontextualizedQuery) {
    const msgDiv = chatInterface.lastUserMessageDiv;
    if (msgDiv) {
 //     msgDiv.innerHTML = chatInterface.currentMessage + "<br><span class=\"decontextualized-query\">" + decontextualizedQuery + "</span>";
    }
  }

  createIntermediateMessageHtml(message) {
    const container = document.createElement('div');
    container.className = 'intermediate-container';
    container.textContent = message;
    console.log("createIntermediateMessageHtml", message);
    return container;
  }

  memoryMessage(itemToRemember, chatInterface) { 
   // console.log("memoryMessage", itemToRemember);
    if (itemToRemember) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `remember-message`;
        messageDiv.textContent = itemToRemember;
        chatInterface.thisRoundRemembered = messageDiv;
        chatInterface.bubble.appendChild(messageDiv);
        return messageDiv;
    }
  }

  getAndProcessResponse(url) {
    //  console.log("getAndProcessResponse", url);
     
    }
  
    resortResults(chatInterface) {
      if (chatInterface.currentItems.length > 0) {
        chatInterface.currentItems.sort((a, b) => b[0].score - a[0].score);
      // Clear existing children
        while (chatInterface.bubble.firstChild) {
          chatInterface.bubble.removeChild(chatInterface.bubble.firstChild);
        }
        if (chatInterface.thisRoundRemembered) {
          chatInterface.bubble.appendChild(chatInterface.thisRoundRemembered)
        }
        // Add sorted domItems back to bubble
        for (const [item, domItem] of chatInterface.currentItems) {
          chatInterface.bubble.appendChild(domItem);
        }
      }
    }
    createInsufficientResultsHtml() {
      const container = document.createElement('div');
      container.className = 'intermediate-container';
      container.appendChild(document.createElement('br'));
      if (this.currentItems.length > 0) {
        container.textContent = "I couldn't find any more results that are relevant to your query.";
      } else {
        container.textContent = "I couldn't find any results that are relevant to your query.";
      }
      container.appendChild(document.createElement('br'));
      return container;
    }
  
    handleFirstMessage(event) {
      this.dotsStillThere = false;
      this.messagesArea.removeChild(this.messagesArea.lastChild);
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
      //  const remoteHost = "http://74.179.100.160:8000";
        const queryString = `query=${encodeURIComponent(message)}&site=${encodeURIComponent(selectedSite)}&model=${encodeURIComponent(selectedModel)}&prev=${prev}&item_to_remember=${encodeURIComponent(this.itemToRemember)}`;
       // const url = `${remoteHost}/?${queryString}`;
        const url = `/?${queryString}`;
       // console.log("url", url);
        this.eventSource = new ManagedEventSource(url);
        this.eventSource.connect(this);
        this.prevMessages.push(message);
        return
      } catch (error) {
        console.error('Error fetching response:', error);
      }
    }
  }
  