/**
 * Created by Nitori on 2017/4/5.
 */
import React from 'react';
import { connect } from 'react-redux';
import classNames from 'classnames';
import validate from 'validate.js';

import i18n from '../../utils/i18n';


const mapStateToProps = (state, ownProps) => {
    const name = ownProps.name;
    return {
        ...state.inputs[name],
        name,
        columns: ownProps.columns ? ownProps.columns : 8,
        row: !!ownProps.row,
        labelName: ownProps.labelName ? ownProps.labelName : name,
        constraints: ownProps.constraints ? ownProps.constraints : {},
        placeholder: ownProps.placeholder ? ownProps.placeholder : '',
    };
};

const mapDispatchToProps = (dispatch, ownProps) => {
    const verifyInput = (value) => {
        const result = validate({ [ownProps.name]: value }, ownProps.constraints, {
            fullMessages: false,
        });
        if (result) {
            dispatch({
                type: 'INPUT_CHANGE_TO_INCORRECT',
                payload: { name: ownProps.name, errInfo: result[ownProps.name] },
            });
        } else {
            dispatch({
                type: 'INPUT_CHANGE_TO_CORRECT',
                payload: { name: ownProps.name },
            });
        }
    };
    return {
        verifyInput,
        handleChanged(e) {
            dispatch({
                type: 'INPUT_CHANGED',
                payload: {
                    name: ownProps.name,
                    value: e.target.value,
                },
            });
            verifyInput(e.target.value);
        },
        handleFocused() {
            dispatch({
                type: 'INPUT_FOCUSED',
                payload: { name: ownProps.name },
            });
        },
        handleBlurred() {
            dispatch({
                type: 'INPUT_BLURRED',
                payload: { name: ownProps.name },
            });
        },
    };
};


@connect(mapStateToProps, mapDispatchToProps)
export default class AttendFormTextboxContainer extends React.PureComponent {
    componentWillMount() {
        this.props.handleBlurred();
        if (this.props.value.length > 0) {
            this.props.verifyInput(this.props.value);
        }
    }

    render() {
        const cn = classNames('textbox has-feedback', {
            'has-fail': (this.props.value.length > 0 && !this.props.isCorrect && this.props.isBlur),
            'has-success': (this.props.value.length > 0 && this.props.isCorrect && !this.props.isBlur),
        });
        const body = (
            <div className={`medium-${this.props.columns} columns`}>
                <label>
                    {i18n(this.props.labelName)}
                </label>
                <input
                    className={cn}
                    type="text"
                    placeholder={i18n(this.props.placeholder)}
                    value={this.props.value}
                    onChange={this.props.handleChanged}
                    onFocus={this.props.handleFocused}
                    onBlur={this.props.handleBlurred}
                />
            </div>
        );

        if (this.props.row) {
            return (
                <div className="row">
                    {body}
                </div>
            );
        }
        return body;
    }
}
