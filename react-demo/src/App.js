import React, { Component } from 'react';
//import logo from './logo.svg';
import './App.css';
import $ from 'jquery';

function titleCase(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

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
      let proofs = this.state.content.proofs.map((p) => <div key={p.html} dangerouslySetInnerHTML={ {__html:p.html} } />);
      let bcrumbs = null;
      if (this.state.content.breadcrumb.length > 0) {
        let listItems = this.state.content.breadcrumb.map((b) => 
      <li><a href={"/tag/" + b.tag}>{titleCase(b.type) + " " + b.ref}</a></li>);
        bcrumbs = <ul className="breadcrumb">{listItems}</ul>
      }
      return (
        <div>
          <h2>Tag {this.state.content.tag.tag}</h2>
        {bcrumbs}        
        <div dangerouslySetInnerHTML={ {__html: this.state.content.tag.html} } />
        {proofs}
        </div>
      );
    }
    else if (this.state.content.hasOwnProperty("type") && this.state.content.type === "chapter") {
      let output=this.state.content.sections.map((s) => <p key={s.tag+s.ref}>
            <a href={"/tag/" + s.tag}>Tag {s.tag}</a> points to Section {s.ref}
            </p>);  
        return (
          <div>
            <h2>Tag {this.state.content.chapter.tag}: Chapter {this.state.content.chapter.ref}</h2>
          <div>{output}</div>
          </div>
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
