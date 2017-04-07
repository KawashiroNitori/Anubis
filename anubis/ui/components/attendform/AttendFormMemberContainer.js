/**
 * Created by Nitori on 2017/4/4.
 */
import React from 'react';
import { connect } from 'react-redux';

import i18n from '../../utils/i18n';
import * as util from '../../misc/Util';
import AttendFormMemberItemContainer from './AttendFormMemberItemContainer';


const mapStateToProps = (state) => ({
    members: state.members.members,
    studentId: state.members.studentId,
    citizenId: state.members.citizenId,
    isPosting: state.members.isPosting,
});

const mapDispatchToProps = (dispatch) => ({
    handleInputChange(e, name) {
        dispatch({
            type: 'STUDENT_INPUT_CHANGED',
            payload: {
                name,
                value: e.target.value,
            },
        });
    },
    handleAddClick(studentId, citizenId) {
        const req = util.get(Context.getSearchUrl, {
            sid: studentId,
            id_num: citizenId,
        });
        dispatch({
            type: 'STUDENT_ADD',
            payload: req,
        });
    },
});


@connect(mapStateToProps, mapDispatchToProps)
export default class AttendFormMemberContainer extends React.PureComponent {
    static handleKeyDown(e) {
        if (e.keyCode === 13) {
            e.preventDefault();
        }
    }

    render() {
        return (
            <div className="row">
                <div className="medium columns">
                    <label>
                        {i18n('Team Members')}
                    </label>
                    {this.props.members.length > 0 &&
                        <table className="data-table no-padding attendform__member-table">
                            <colgroup>
                                <col className="col--name" />
                                <col className="col--class" />
                                <col className="col--college" />
                                <col className="col--toolbar" />
                            </colgroup>
                            <thead>
                                <tr>
                                    <th className="col--name">
                                        {i18n('Name')}
                                    </th>
                                    <th className="col--class">
                                        {i18n('Class')}
                                    </th>
                                    <th className="col--college">
                                        {i18n('College')}
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                {this.props.members.map((member) => (
                                    <AttendFormMemberItemContainer
                                        key={member._id}
                                        member={member}
                                    />
                                ))}
                            </tbody>
                        </table>
                    }
                    {this.props.members.length < 3 &&
                        <div className="row">
                            <div className="medium-3 columns">
                                <input
                                    className="textbox"
                                    type="text"
                                    placeholder={i18n('Student ID')}
                                    maxLength="20"
                                    value={this.props.studentId}
                                    onChange={(e) => this.props.handleInputChange(e, 'studentId')}
                                />
                            </div>
                            <div className="medium-3 columns">
                                <input
                                    className="textbox"
                                    type="text"
                                    placeholder={i18n('Last 6 digits of Citizen ID')}
                                    maxLength="6"
                                    value={this.props.citizenId}
                                    onChange={(e) => this.props.handleInputChange(e, 'citizenId')}
                                />
                            </div>
                            <div className="medium-3 columns">
                                <button
                                    className="primary rounded button small"
                                    disabled={!(this.props.studentId.length > 0
                                    && this.props.citizenId.length === 6
                                    && !this.props.isPosting)}
                                    onClick={() => this.props.handleAddClick(this.props.studentId, this.props.citizenId)}
                                >
                                    {this.props.isPosting
                                        ? (<span><span className="icon icon-hourglass" />{i18n('Verifying...')}</span>)
                                        : (<span><span className="icon icon-add" />{i18n('Add')}</span>)
                                    }
                                </button>
                            </div>
                            <div className="medium-3 columns" />
                        </div>
                    }
                    </div>
            </div>
        );
    }
}
