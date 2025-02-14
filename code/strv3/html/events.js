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
  
 
 