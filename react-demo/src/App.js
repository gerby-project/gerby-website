import React, { Component } from 'react';
import logo from './logo.svg';
import './App.css';
import $ from 'jquery';

class App extends Component {
  componentWillMount() {
    this.state = {content: {}};
    var that = this;
    var pathname = "/" + window.location.href.split("?")[1];
    if (pathname === "/undefined") {
      pathname = window.location.pathname;
    }
    var url = "http://127.0.0.1:5000/api" + pathname + "?callback=?";
    $.getJSON(url,
    function (result) {
      that.setState({content:result});
      window.MathJax.Hub.Queue(["Typeset",window.MathJax.Hub]);
    });
  }

  componentDidUpdate() {
    window.MathJax.Hub.Queue(["Typeset",window.MathJax.Hub]);
  }
  
  render() {
    if (this.state.content.hasOwnProperty("type") && this.state.content.type === "tag") {
      var that = this;
      function spawnStatement() {
        return {__html: that.state.content.tag.html};
      }
      function spawnProof(i) {
        return {__html: that.state.content.proofs[i].html}
      }
      var proofs = [];
      for (var i = 0; i < that.state.content.proofs.length; i++) {
        proofs.push(<div dangerouslySetInnerHTML={spawnProof(i)}></div>)
      }

      return (
        <div>
        <div dangerouslySetInnerHTML={spawnStatement()}>
        </div>
        {proofs}
        </div>
      );
    }
    else if (this.state.content.hasOwnProperty("type") && this.state.content.type === "chapter") {
      console.log(this.state.content.sections);
        var N = this.state.content.sections.length;
        var output = [];
        for (var i = 0; i < N; i++){
          output.push(<p>
            <a href={"/tag/" + this.state.content.sections[i].tag}>Tag {this.state.content.sections[i].tag}</a> points to Section {this.state.content.sections[i].ref}
            </p>)
        }
        return (
          <div>{output}</div>
        )
    }
    else {
    return (
      <div className="App">
        <p className="App-intro">
          Waiting for stuff.
        </p>
      </div>
    );
    }
  }
}

export default App;
